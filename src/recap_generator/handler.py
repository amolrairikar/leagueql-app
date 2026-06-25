"""AI weekly matchup recap generator — ECS Fargate task for LeagueQL (BE-022).

Launched fire-and-forget (via ``ecs:RunTask``) by (A) the Stripe webhook on a real
subscription activation and (B) the processor at the end of every onboard/refresh.
Both paths run the same idempotent, premium-gated backfill: enumerate every season
and every completed week the league has, skip any ``(season, week)`` that already
has a recap, and generate the rest via AWS Bedrock (``common.bedrock``).

This runs as a **Fargate task** rather than a Lambda because a full multi-season
backfill at the model's low requests-per-minute quota can exceed the 15-minute
Lambda cap; a task has no such limit. Per-league input arrives as **container
environment overrides** (set by the trigger's ``run_task`` call), and ``main()`` is
the container entrypoint.

Recaps are cached as ``MATCHUP_RECAP#{season}#WEEK#{week:02d}`` items and read back
by the frontend through the query API (BE-005); generation never happens on the
request path.
"""

import datetime
import json
import os
import threading
import time
from decimal import Decimal

import boto3
import botocore.config
from boto3.dynamodb.conditions import Key

from common.bedrock import generate_recap
from common.feature_flags import (
    PREMIUM_FEATURE,
    is_billing_enabled,
    is_feature_paywalled,
)
from common.logging_utils import correlation_id_var, logger
from common.tracing import init_tracing, traced_handler

# Continue the upstream trace (processor on trigger B, Stripe webhook on trigger A)
# → Axiom (BE-021). A no-op unless Axiom is configured, so tests / unconfigured
# envs are unaffected.
init_tracing("leagueql-recap-generator")

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_table_name = os.environ["DYNAMODB_TABLE_NAME"]
_table = boto3.resource("dynamodb", config=_retry_config).Table(_table_name)

# The throughput ceiling is the model's Bedrock **requests-per-minute** quota, not
# parallelism: a single Converse call (a few seconds) is faster than the required
# spacing, so the rate cap — not call latency — is the bottleneck, and running calls
# concurrently only bursts past the RPM limit and throttles. Recaps are therefore
# generated **sequentially**, paced so request starts stay under the quota.
#
# Minimum spacing between Converse request starts, in seconds. The floor is
# ``60 / RPM`` (e.g. an 8-RPM model needs >= 7.5s); the default leaves headroom for
# the sliding-window boundary and the occasional adaptive retry. Tune to the model's
# RPM quota (raise if still throttling; lower after a quota increase). 0 disables
# pacing (tests). Steady-state — one new week per refresh — is a single call, so
# pacing is effectively free there; it only matters for multi-week backfills. The
# Fargate task has no 15-min cap, so even a full multi-season backfill runs to
# completion at this pace.
_MIN_REQUEST_INTERVAL = max(
    0.0, float(os.environ.get("RECAP_MIN_REQUEST_INTERVAL_SECONDS", "10"))
)


class _RateLimiter:
    """Thread-safe minimum-interval gate between Converse request starts.

    Reserves the next slot under a lock (cheap) and sleeps outside it. Thread-safe in
    case workers are ever reintroduced; today the generation loop is sequential.
    """

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def acquire(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next_allowed)
            self._next_allowed = start + self._min_interval
            wait = start - now
        if wait > 0:
            time.sleep(wait)


_rate_limiter = _RateLimiter(_MIN_REQUEST_INTERVAL)


# How many top performers from each side to include in the highlights, trimmed to
# keep the prompt's input tokens low.
_TOP_STARTERS = 2
_TOP_BENCH = 1


def _convert_decimals(obj):
    """Recursively convert DynamoDB ``Decimal``s to JSON-friendly int/float."""
    if isinstance(obj, list):
        return [_convert_decimals(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def main() -> None:
    """Container entrypoint: read the per-league input from environment overrides
    (set by the trigger's ``run_task`` call), continue the upstream trace (BE-021),
    and run the generator.

    Inputs (env): ``CANONICAL_LEAGUE_ID`` (required), ``PLATFORM``,
    ``NATIVE_LEAGUE_ID``, ``CORRELATION_ID``, and ``TRACE_CONTEXT`` (a JSON-encoded
    W3C carrier so the task's span continues the processor/webhook trace).
    """
    event = {
        "canonical_league_id": os.environ.get("CANONICAL_LEAGUE_ID"),
        "platform": os.environ.get("PLATFORM"),
        "native_league_id": os.environ.get("NATIVE_LEAGUE_ID"),
        "correlation_id": os.environ.get("CORRELATION_ID"),
    }
    carrier = None
    raw_carrier = os.environ.get("TRACE_CONTEXT")
    if raw_carrier:
        try:
            carrier = json.loads(raw_carrier)
        except (ValueError, TypeError):
            logger.warning("Invalid TRACE_CONTEXT; starting a fresh trace")
    with traced_handler("recap_generator.handle", carrier=carrier):
        result = _handle(event)
    logger.info("Recap generator task finished: %s", result)


def _handle(event) -> dict:
    correlation_id_var.set(event.get("correlation_id") or "")
    canonical_league_id = event.get("canonical_league_id")
    if not canonical_league_id:
        logger.error("recap_generator invoked without canonical_league_id; skipping")
        return {"status": "skipped", "reason": "missing_canonical_league_id"}

    logger.info(
        "Recap generation requested: league=%s platform=%s",
        canonical_league_id,
        event.get("platform"),
    )

    # Server-side premium gate (before any Bedrock spend). Billing off → recaps are
    # ungated on the read path but never generated by these triggers, so no-op.
    if not is_billing_enabled():
        logger.info("Billing disabled; recap generation skipped")
        return {"status": "skipped", "reason": "billing_disabled"}

    metadata = _get_metadata(canonical_league_id)
    if is_feature_paywalled(PREMIUM_FEATURE) and not _is_subscription_active(metadata):
        logger.info(
            "League %s has no active subscription; recap generation skipped",
            canonical_league_id,
        )
        return {"status": "skipped", "reason": "not_premium"}

    seasons = _get_league_seasons(canonical_league_id)
    if not seasons:
        logger.info("League %s has no seasons; nothing to recap", canonical_league_id)
        return {"status": "completed", "generated": 0}

    model_id = os.environ["BEDROCK_MODEL_ID"]
    work: list[tuple[str, str, dict]] = []
    for season in seasons:
        weeks = _get_matchup_weeks(canonical_league_id, season)
        if not weeks:
            continue
        standings = _get_standings(canonical_league_id, season)
        existing = _get_existing_recap_weeks(canonical_league_id, season)
        for week, matchups in weeks.items():
            if week in existing:
                continue
            highlights = _build_highlights(season, week, matchups, standings)
            work.append((season, week, highlights))

    if not work:
        logger.info(
            "League %s already has recaps for every completed week; no-op",
            canonical_league_id,
        )
        return {"status": "completed", "generated": 0}

    logger.info(
        "Generating %d weekly recap(s) for league %s", len(work), canonical_league_id
    )
    generated = _generate_and_store(canonical_league_id, work, model_id)
    logger.info(
        "Recap generation finished: league=%s generated=%d of %d",
        canonical_league_id,
        generated,
        len(work),
    )
    return {"status": "completed", "generated": generated}


def _generate_and_store(
    canonical_league_id: str, work: list[tuple[str, str, dict]], model_id: str
) -> int:
    """Generate each week's recap sequentially (rate-paced) and store the successes.

    Each iteration waits on the rate limiter so request starts stay under the model's
    RPM quota. Per-week failures are caught and logged so one Bedrock failure never
    aborts the batch; the idempotent skip means a later run regenerates only the
    still-missing weeks. Runs in a Fargate task, so there is no invocation time cap.
    """
    generated = 0
    for season, week, highlights in work:
        _rate_limiter.acquire()
        try:
            recap = generate_recap(highlights)
            _store_recap(canonical_league_id, season, week, recap, model_id)
            generated += 1
        except Exception as exc:
            logger.error(
                "Failed to generate recap for league=%s season=%s week=%s: %s",
                canonical_league_id,
                season,
                week,
                exc,
            )
    return generated


def _get_metadata(canonical_league_id: str) -> dict:
    resp = _table.get_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"}
    )
    return resp.get("Item", {})


def _is_subscription_active(metadata: dict) -> bool:
    """True while ``now < subscription_end_time`` (mirrors BE-014's comparison).

    An absent or past ``subscription_end_time`` is treated as expired.
    """
    end_time = metadata.get("subscription_end_time")
    if not end_time:
        return False
    try:
        end = datetime.datetime.fromisoformat(end_time)
    except (ValueError, TypeError):
        return False
    return datetime.datetime.now(datetime.timezone.utc) < end


def _get_league_seasons(canonical_league_id: str) -> list[str]:
    """All seasons the league has, via the GSI1 LEAGUE_LOOKUP index.

    Mirrors the API's ``get_league_seasons``: a league may have multiple lookup
    items (Sleeper), so merge their season sets. Returns sorted unique seasons.
    """
    resp = _table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("canonical_league_id").eq(canonical_league_id),
    )
    seasons: set[str] = set()
    for item in resp.get("Items", []):
        seasons.update(item.get("seasons", set()))
    return sorted(seasons)


def _get_matchup_weeks(canonical_league_id: str, season: str) -> dict[str, list]:
    """Return ``{week2: matchups}`` for every completed week of a season.

    Presence of a ``MATCHUPS#{season}#WEEK#{week}`` item implies the week is
    complete (there is no in-progress flag). ``week2`` is the zero-padded week from
    the SK, used directly as the recap SK suffix.
    """
    weeks: dict[str, list] = {}
    kwargs = {
        "KeyConditionExpression": Key("PK").eq(f"LEAGUE#{canonical_league_id}")
        & Key("SK").begins_with(f"MATCHUPS#{season}#"),
    }
    while True:
        resp = _table.query(**kwargs)
        for item in resp.get("Items", []):
            # SK: MATCHUPS#{season}#WEEK#{week2}
            week2 = item["SK"].split("#")[-1]
            weeks[week2] = _convert_decimals(item.get("data", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return weeks


def _get_standings(canonical_league_id: str, season: str) -> dict[str, dict]:
    """Return ``{team_id: standings_row}`` for the season, for records/context."""
    resp = _table.get_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": f"STANDINGS#{season}"}
    )
    rows = _convert_decimals(resp.get("Item", {}).get("data", []))
    return {str(row.get("team_id")): row for row in rows}


def _get_existing_recap_weeks(canonical_league_id: str, season: str) -> set[str]:
    """Return the set of zero-padded weeks that already have a recap (idempotency)."""
    existing: set[str] = set()
    kwargs = {
        "KeyConditionExpression": Key("PK").eq(f"LEAGUE#{canonical_league_id}")
        & Key("SK").begins_with(f"MATCHUP_RECAP#{season}#WEEK#"),
        "ProjectionExpression": "SK",
    }
    while True:
        resp = _table.query(**kwargs)
        for item in resp.get("Items", []):
            existing.add(item["SK"].split("#")[-1])
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return existing


def _top_performers(players: list, limit: int) -> list[dict]:
    """Top ``limit`` players by points, trimmed to name/position/points."""
    ranked = sorted(players, key=lambda p: p.get("points_scored") or 0, reverse=True)
    return [
        {
            "name": p.get("full_name"),
            "position": p.get("position"),
            "points": p.get("points_scored"),
        }
        for p in ranked[:limit]
    ]


def _team_side(prefix: str, matchup: dict, standings: dict) -> dict:
    """Build one side's highlight block from a matchup row + standings context."""
    team_id = str(matchup.get(f"{prefix}_id"))
    row = standings.get(team_id, {})
    return {
        "manager": matchup.get(f"{prefix}_display_name"),
        "team_name": matchup.get(f"{prefix}_team_name"),
        "record": row.get("record"),
        "score": matchup.get(f"{prefix}_score"),
        "top_starters": _top_performers(
            matchup.get(f"{prefix}_starters") or [], _TOP_STARTERS
        ),
        "top_bench": _top_performers(matchup.get(f"{prefix}_bench") or [], _TOP_BENCH),
    }


def _build_highlights(season: str, week: str, matchups: list, standings: dict) -> dict:
    """Assemble the JSON highlights for one week sent to the model."""
    games = []
    for m in matchups:
        # Skip self-matchup placeholders (byes) — they are not real games.
        if str(m.get("team_a_id")) == str(m.get("team_b_id")):
            continue
        a = _team_side("team_a", m, standings)
        b = _team_side("team_b", m, standings)
        winner_id = m.get("winner")
        score_a = m.get("team_a_score") or 0
        score_b = m.get("team_b_score") or 0
        games.append(
            {
                "team_a": a,
                "team_b": b,
                "winner": (
                    a["manager"]
                    if str(winner_id) == str(m.get("team_a_id"))
                    else b["manager"]
                    if str(winner_id) == str(m.get("team_b_id"))
                    else None
                ),
                "margin": round(abs(score_a - score_b), 2),
                "playoff_round": m.get("playoff_round"),
            }
        )
    return {"season": season, "week": int(week), "matchups": games}


def _store_recap(
    canonical_league_id: str, season: str, week: str, recap: dict, model_id: str
) -> None:
    """Write one cached recap item (idempotent skip means we only write missing weeks)."""
    # ``data`` is a single-element list so the query API's exact-get path (which
    # returns ``item["data"]`` verbatim into ``QueryResponse.data: list``) and the
    # frontend's ``queryLeague<RecapItem>`` → ``{data: RecapItem[]}`` contract both
    # hold, consistent with every other precomputed view.
    _table.put_item(
        Item={
            "PK": f"LEAGUE#{canonical_league_id}",
            "SK": f"MATCHUP_RECAP#{season}#WEEK#{week}",
            "data": [
                {
                    "headline": recap["headline"],
                    "body": recap["body"],
                    "generated_at": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "model": model_id,
                }
            ],
        }
    )


if __name__ == "__main__":  # pragma: no cover
    main()
