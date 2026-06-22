"""AI weekly recap generator Lambda (BE-022).

Invoked asynchronously by the Stripe billing webhook on a genuine premium
activation (``InvocationType="Event"``) with
``{canonical_league_id, correlation_id, trace_context}``. Backfills an AI recap
for every historical season/week of the league that has matchups, idempotently
(an existing ``RECAP`` item for a week is skipped — safe under Stripe's
at-least-once delivery, renewals, partial-completion retries, and re-upgrades).

Mirrors the existing async workers (``sleeper_refresh``, ``processor``): module-load
``init_tracing`` + a ``traced_handler`` span continuing the webhook's trace
(BE-021), a best-effort ``JOB_STATUS`` item (BE-008), and a feature-flag gate.

Generation cost is controlled three ways: premium-only (feature-flag +
subscription re-check), deterministic highlights in / prose out (no number
hallucination, bounded tokens), and per-week idempotency (no double-spend).
"""

import concurrent.futures
import datetime
import os

import boto3
import botocore.config
from boto3.dynamodb.conditions import Key

from common.feature_flags import PREMIUM_FEATURE, is_feature_paywalled
from common.job_status import write_job_status
from common.logging_utils import logger
from common.tracing import init_tracing, traced_handler
from generate import RecapGenerationError, MODEL_ID, generate_recap
from highlights import compute_highlights

# Continue the end-to-end trace the webhook started (BE-021). No-op unless Axiom
# is configured, so tests / unconfigured envs are unaffected.
init_tracing("leagueql-ai-recap")

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_dynamodb = boto3.resource("dynamodb", config=_retry_config)

# How many weeks to generate concurrently. Bedrock enforces per-account
# requests/tokens-per-minute quotas on Nova Lite, so this is deliberately small —
# a bounded pool collapses the backfill's wall-clock time while the Bedrock
# client's own retry/backoff absorbs the occasional throttle. Tune via env.
MAX_CONCURRENCY = max(1, int(os.environ.get("RECAP_MAX_CONCURRENCY", "4")))


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
                    "model": MODEL_ID,
                    "generated_at": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                }
            ],
        }
    )


def _generate_and_write(table, canonical_league_id: str, work: dict) -> bool:
    """Generate + persist one week's recap. Returns True on success, False on a
    handled generation failure. Runs in a worker thread (the boto3 Bedrock client
    and the DynamoDB client are thread-safe); reads were done up front, so the only
    DynamoDB call here is the per-week ``put_item``.
    """
    season, ww, week = work["season"], work["ww"], work["week"]
    try:
        recap = generate_recap(work["highlights"], season, week)
    except RecapGenerationError:
        return False
    except Exception:
        logger.exception(
            "Unexpected error generating recap for %s %s week %s",
            canonical_league_id,
            season,
            ww,
        )
        return False

    _write_recap(table, canonical_league_id, season, ww, week, recap)
    return True


def lambda_handler(event, context) -> dict:
    """Backfill AI recaps for every un-recapped week of a premium league.

    Always returns a summary dict; per-week generation failures are recorded on
    JOB_STATUS (failure_code ``RECAP``) but do not raise, so one bad week never
    loses the others. Weeks are generated concurrently (bounded by
    ``MAX_CONCURRENCY``) to keep the backfill within the Lambda timeout.
    """
    canonical_league_id = event.get("canonical_league_id")
    correlation_id = event.get("correlation_id")
    logger.info(
        "AI recap backfill: canonical_league_id=%s correlation_id=%s",
        canonical_league_id,
        correlation_id,
    )

    with traced_handler("ai_recap", carrier=event.get("trace_context")):
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

        generated = 0
        failed = 0
        if work_items:
            workers = min(MAX_CONCURRENCY, len(work_items))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                results = pool.map(
                    lambda w: _generate_and_write(table, canonical_league_id, w),
                    work_items,
                )
                for ok in results:
                    if ok:
                        generated += 1
                    else:
                        failed += 1

        status = "FAILED" if failed else "COMPLETED"
        write_job_status(
            correlation_id,
            status,
            failure_code="RECAP" if failed else None,
            canonical_league_id=canonical_league_id,
        )
        logger.info(
            "AI recap backfill done: generated=%d skipped=%d failed=%d",
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
