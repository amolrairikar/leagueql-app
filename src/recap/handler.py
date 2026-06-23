"""AI weekly recap generator Lambda (BE-022).

Invoked asynchronously by the Stripe billing webhook on a genuine premium
activation (``InvocationType="Event"``) with
``{canonical_league_id, correlation_id, trace_context}``. Backfills an recap
for every historical season/week of the league that has matchups, idempotently
(an existing ``RECAP`` item for a week is skipped — safe under Stripe's
at-least-once delivery, renewals, partial-completion retries, and re-upgrades).

Mirrors the existing async workers (``sleeper_refresh``, ``processor``): module-load
``init_tracing`` + a ``traced_handler`` span continuing the webhook's trace
(BE-021), a best-effort ``JOB_STATUS`` item (BE-008), and a feature-flag gate.

Generation is controlled two ways: premium-only (feature-flag + subscription
re-check) and per-week idempotency (an existing RECAP item is skipped). Recaps are
composed by ``compose.py`` (deterministic outline → Bedrock Nova Premier → numeric
validation → deterministic snippet fallback); since each week is an independent
Bedrock call, the per-week generations run on a small bounded thread pool while the
DynamoDB writes stay serial.
"""

import datetime
import os
from concurrent.futures import ThreadPoolExecutor

import boto3
import botocore.config
from boto3.dynamodb.conditions import Key

from common.feature_flags import PREMIUM_FEATURE, is_feature_paywalled
from common.job_status import write_job_status
from common.logging_utils import logger
from common.tracing import init_tracing, traced_handler
from compose import RecapGenerationError, generate_recap
from highlights import compute_highlights

# Bound on concurrent per-week Bedrock generations during a backfill. Generation
# is network-bound (an LLM call per week), so a small pool keeps backfill latency
# down without overwhelming Bedrock throttling limits.
_MAX_GENERATE_WORKERS = 8

# Continue the end-to-end trace the webhook started (BE-021). No-op unless Axiom
# is configured, so tests / unconfigured envs are unaffected.
init_tracing("leagueql-recap")

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_dynamodb = boto3.resource("dynamodb", config=_retry_config)


def _table():
    return _dynamodb.Table(os.environ["DYNAMODB_TABLE_NAME"])


def _subscription_active(table, canonical_league_id: str) -> bool:
    """Return True when the league's ``subscription_end_time`` is in the future.

    Re-checks METADATA so an upgrade canceled before this Lambda runs does not
    generate. Missing item / missing attribute / unparseable value all fail closed.
    """
    resp = table.get_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
        ProjectionExpression="subscription_end_time",
    )
    end_time = resp.get("Item", {}).get("subscription_end_time")
    if not end_time:
        return False
    try:
        return datetime.datetime.fromisoformat(end_time) > datetime.datetime.now(
            datetime.timezone.utc
        )
    except (ValueError, TypeError):
        return False


def _iter_matchup_items(table, canonical_league_id: str):
    """Yield every ``MATCHUPS#...`` item for the league (paginated)."""
    pk = f"LEAGUE#{canonical_league_id}"
    kwargs = {
        "KeyConditionExpression": Key("PK").eq(pk) & Key("SK").begins_with("MATCHUPS#"),
    }
    while True:
        resp = table.query(**kwargs)
        yield from resp.get("Items", [])
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key


def _weekly_standings_rows(table, canonical_league_id: str, season: str) -> list[dict]:
    """Return the ``WEEKLY_STANDINGS#{season}`` data rows, or ``[]`` if absent."""
    resp = table.get_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": f"WEEKLY_STANDINGS#{season}"}
    )
    item = resp.get("Item")
    return item.get("data", []) if item else []


def _parse_matchups_sk(sk: str) -> tuple[str, str] | None:
    """Parse ``MATCHUPS#{season}#WEEK#{WW}`` → (season, WW). None if malformed."""
    parts = sk.split("#")
    if len(parts) != 4 or parts[0] != "MATCHUPS" or parts[2] != "WEEK":
        return None
    return parts[1], parts[3]


def _recap_exists(table, canonical_league_id: str, season: str, ww: str) -> bool:
    resp = table.get_item(
        Key={
            "PK": f"LEAGUE#{canonical_league_id}",
            "SK": f"RECAP#{season}#WEEK#{ww}",
        },
        ProjectionExpression="SK",
    )
    return "Item" in resp


def _write_recap(
    table, canonical_league_id: str, season: str, ww: str, week: str, recap: dict
) -> None:
    table.put_item(
        Item={
            "PK": f"LEAGUE#{canonical_league_id}",
            "SK": f"RECAP#{season}#WEEK#{ww}",
            # `data` is a single-element list (one recap object) to match every
            # other view's shape, so the BE-005 query path returns it generically
            # (the endpoint's QueryResponse.data is a list).
            "data": [
                {
                    "season": season,
                    "week": week,
                    "headline": recap["headline"],
                    "body": recap["body"],
                    # The generator that produced this recap (Bedrock model id for an
                    # AI recap, "snippet-v1" for the deterministic fallback).
                    "model": recap["model"],
                    "generated_at": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                }
            ],
        }
    )


def _generate_one(canonical_league_id: str, work: dict) -> dict | None:
    """Compose one week's recap. Returns the recap dict, or ``None`` on a handled
    generation failure (so a bad week never loses the others). Pure compute + the
    Bedrock call — no DynamoDB — so it is safe to run concurrently across weeks.
    """
    season, ww = work["season"], work["ww"]
    try:
        return generate_recap(work["highlights"], season, work["week"])
    except RecapGenerationError:
        return None
    except Exception:
        logger.exception(
            "Unexpected error generating recap for %s %s week %s",
            canonical_league_id,
            season,
            ww,
        )
        return None


def lambda_handler(event, context) -> dict:
    """Backfill recaps for every un-recapped week of a premium league.

    Always returns a summary dict; per-week generation failures are recorded on
    JOB_STATUS (failure_code ``RECAP``) but do not raise, so one bad week never
    loses the others.
    """
    canonical_league_id = event.get("canonical_league_id")
    correlation_id = event.get("correlation_id")
    logger.info(
        "recap backfill: canonical_league_id=%s correlation_id=%s",
        canonical_league_id,
        correlation_id,
    )

    with traced_handler("recap", carrier=event.get("trace_context")):
        if not canonical_league_id:
            logger.warning("No canonical_league_id in event; nothing to do")
            return {"status": "skipped", "reason": "no_league"}

        # Premium gate: only paywalled premium leagues generate recaps (cost).
        if not is_feature_paywalled(PREMIUM_FEATURE):
            logger.info("premium_feature not paywalled; skipping recap generation")
            return {"status": "skipped", "reason": "not_paywalled"}

        table = _table()

        # Re-check the subscription is still active (an upgrade canceled before
        # this async run must not generate).
        if not _subscription_active(table, canonical_league_id):
            logger.info(
                "Subscription not active for %s; skipping recap generation",
                canonical_league_id,
            )
            return {"status": "skipped", "reason": "subscription_inactive"}

        skipped = 0
        # Cache weekly-standings per season across that season's weeks.
        standings_cache: dict[str, list[dict]] = {}
        # Build the work list with all DynamoDB *reads* up front (single-threaded),
        # so the standings cache and idempotency checks are race-free; only the
        # generate + write step below is parallelized.
        work_items: list[dict] = []
        for item in _iter_matchup_items(table, canonical_league_id):
            parsed = _parse_matchups_sk(item.get("SK", ""))
            if not parsed:
                continue
            season, ww = parsed
            week = str(int(ww))  # un-padded week, matching the matchup row `week`

            if _recap_exists(table, canonical_league_id, season, ww):
                skipped += 1
                continue

            if season not in standings_cache:
                standings_cache[season] = _weekly_standings_rows(
                    table, canonical_league_id, season
                )

            work_items.append(
                {
                    "season": season,
                    "ww": ww,
                    "week": week,
                    "highlights": compute_highlights(
                        item.get("data", []), standings_cache[season], season, week
                    ),
                }
            )

        # Generate weeks concurrently (each is an independent Bedrock call), then
        # write serially — the DynamoDB Table resource isn't guaranteed thread-safe,
        # and the Bedrock call is what dominates latency. ``map`` preserves order, so
        # writes stay in week order.
        generated = 0
        failed = 0
        if work_items:
            workers = min(_MAX_GENERATE_WORKERS, len(work_items))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                recaps = pool.map(
                    lambda w: (w, _generate_one(canonical_league_id, w)), work_items
                )
            for work, recap in recaps:
                if recap is None:
                    failed += 1
                    continue
                _write_recap(
                    table,
                    canonical_league_id,
                    work["season"],
                    work["ww"],
                    work["week"],
                    recap,
                )
                generated += 1

        status = "FAILED" if failed else "COMPLETED"
        write_job_status(
            correlation_id,
            status,
            failure_code="RECAP" if failed else None,
            canonical_league_id=canonical_league_id,
        )
        logger.info(
            "recap backfill done: generated=%d skipped=%d failed=%d",
            generated,
            skipped,
            failed,
        )
        return {
            "status": status.lower(),
            "generated": generated,
            "skipped": skipped,
            "failed": failed,
        }
