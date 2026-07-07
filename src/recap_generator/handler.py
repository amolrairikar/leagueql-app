"""AI weekly matchup recap generator — scheduled Fargate task for LeagueQL (BE-021).

Runs on an EventBridge cron (every 15 min) as a one-shot ECS Fargate task. Each run it
processes the whole ``RECAP_QUEUE`` partition: for every pending league it premium-gates,
enumerates every season's completed weeks, drops already-recapped weeks, builds the
matchup highlights, and generates each missing week's recap **synchronously** via the
Anthropic API (Claude Haiku 4.5), writing the ``MATCHUP_RECAP#{season}#WEEK#{week}`` item
right there with an ``attribute_not_exists(SK)`` conditional put (idempotent — re-runs
skip already-written weeks).

Generation is paced under the account's ~50 RPM ceiling by an in-process rate limiter
(``RECAP_MAX_RPM``); the SDK additionally retries transient ``429``/``5xx``. A league's
pending marker is deleted only when **all** its missing weeks were written; if any week
raised, the marker is left pending so the next scheduled run retries the rest. Running as
a Fargate task (not a Lambda) means a large backlog drains in one run without a 15-minute
timeout. Roots its own trace (BE-020).

No-ops when billing is disabled or the ``recap`` kill-switch flag is OFF (BE-017) — the
latter lets DEV suppress the LLM spend while keeping billing on for subscription testing.
"""

import datetime
import os
import time
from decimal import Decimal

import boto3
import botocore.config
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from common.feature_flags import (
    PREMIUM_FEATURE,
    is_billing_enabled,
    is_feature_paywalled,
    is_recap_enabled,
)
from common.logging_utils import correlation_id_var, logger
from common.recap_llm import generate_recap
from common.tracing import init_tracing, traced_handler

# Roots its own trace (no upstream carrier): the scheduled run processes many leagues, so
# it cannot continue any single trigger's span (BE-020). A no-op unless Axiom is configured.
init_tracing("leagueql-recap-generator")

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_table_name = os.environ["DYNAMODB_TABLE_NAME"]
_table = boto3.resource("dynamodb", config=_retry_config).Table(_table_name)

_QUEUE_PK = "RECAP_QUEUE"

# Recorded on each generated MATCHUP_RECAP item (provenance) and sent to the API.
_MODEL_ID = os.environ["RECAP_MODEL_ID"]

# Pace synchronous calls under the account's RPM ceiling (~50 RPM, tier-dependent); the
# default leaves headroom. The SDK still retries any 429 that slips through.
_MAX_RPM = float(os.environ.get("RECAP_MAX_RPM", "45"))
_MIN_INTERVAL_S = 60.0 / _MAX_RPM if _MAX_RPM > 0 else 0.0
_last_call_monotonic = 0.0

# How many top performers from each side to include in the highlights, trimmed to keep
# the prompt's input tokens low.
_TOP_STARTERS = 2
_TOP_BENCH = 1


def main():  # pragma: no cover - thin entrypoint
    """Container entrypoint. Roots a fresh trace and processes the recap queue."""
    with traced_handler("recap_generator.handle", root=True):
        result = _handle()
    logger.info("Recap generator finished: %s", result)
    return result


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _handle() -> dict:
    if not is_billing_enabled():
        logger.info("Billing disabled; recap generator skipped")
        return {"status": "skipped", "reason": "billing_disabled"}

    if not is_recap_enabled():
        logger.info("Recaps disabled by feature flag; recap generator skipped")
        return {"status": "skipped", "reason": "recap_disabled"}

    markers = _get_pending_markers()
    if not markers:
        logger.info("No pending recap work")
        return {"status": "completed", "leagues": 0, "written": 0, "failed": 0}

    logger.info(
        "Recap generator starting: %d pending league(s) (model=%s, max_rpm=%s)",
        len(markers),
        _MODEL_ID,
        _MAX_RPM,
    )
    written = 0
    failed = 0
    for index, marker in enumerate(markers, start=1):
        canonical_league_id = marker["canonical_league_id"]
        correlation_id_var.set(marker.get("correlation_id") or "")
        logger.info(
            "Processing league %d/%d: %s",
            index,
            len(markers),
            canonical_league_id,
        )
        outcome = _process_league(canonical_league_id)
        written += outcome["written"]
        failed += outcome["failed"]

    logger.info(
        "Recap run processed %d league(s): %d written, %d failed",
        len(markers),
        written,
        failed,
    )
    return {
        "status": "completed",
        "leagues": len(markers),
        "written": written,
        "failed": failed,
    }


def _process_league(canonical_league_id: str) -> dict:
    """Generate + write every missing week's recap for one pending league.

    Premium-gates first (a non-premium league's marker is deleted with no spend). Returns
    ``{"written": int, "failed": int}``; the marker is deleted only when no week failed.
    """
    metadata = _get_metadata(canonical_league_id)
    if is_feature_paywalled(PREMIUM_FEATURE) and not _is_subscription_active(metadata):
        logger.info(
            "League %s has no active subscription; dropping from recap queue",
            canonical_league_id,
        )
        _delete_marker(canonical_league_id)
        return {"written": 0, "failed": 0}

    seasons = _get_league_seasons(canonical_league_id)
    logger.info(
        "League %s: %d season(s) to scan (%s)",
        canonical_league_id,
        len(seasons),
        ", ".join(seasons) or "none",
    )
    written = 0
    failed = 0
    for season in seasons:
        weeks = _get_matchup_weeks(canonical_league_id, season)
        if not weeks:
            continue
        # Cumulative record AS OF each week (WEEKLY_STANDINGS); fall back to the
        # season-final STANDINGS for weeks with no snapshot (e.g. playoff weeks), so a
        # Week 7 recap shows the Week 7 record, not the end-of-season record.
        final_standings = _get_standings(canonical_league_id, season)
        weekly_standings = _get_weekly_standings(canonical_league_id, season)
        existing = _get_existing_recap_weeks(canonical_league_id, season)
        missing = {w: m for w, m in weeks.items() if w not in existing}
        if not missing:
            logger.info(
                "League %s season %s: all %d week(s) already recapped",
                canonical_league_id,
                season,
                len(weeks),
            )
            continue
        logger.info(
            "League %s season %s: generating %d of %d week(s) (%d already present)",
            canonical_league_id,
            season,
            len(missing),
            len(weeks),
            len(existing),
        )
        for week, matchups in missing.items():
            week_standings = weekly_standings.get(_week_int(week)) or final_standings
            try:
                if _generate_and_write(
                    canonical_league_id, season, week, matchups, week_standings
                ):
                    written += 1
            except Exception:
                logger.exception(
                    "Recap generation failed for league=%s season=%s week=%s",
                    canonical_league_id,
                    season,
                    week,
                )
                failed += 1

    if failed == 0:
        # Every missing week is now written (or was already) — clear the marker.
        logger.info(
            "League %s recap pass complete: %d written; clearing marker",
            canonical_league_id,
            written,
        )
        _delete_marker(canonical_league_id)
    else:
        logger.warning(
            "Leaving recap marker pending for league=%s (%d written, %d week(s) "
            "failed); next run retries them",
            canonical_league_id,
            written,
            failed,
        )
    return {"written": written, "failed": failed}


def _generate_and_write(
    canonical_league_id: str, season: str, week: str, matchups: list, standings: dict
) -> bool:
    """Generate one week's recap and write it idempotently. Returns True if newly written."""
    highlights = _build_highlights(season, week, matchups, standings)
    logger.info(
        "Generating recap for league=%s season=%s week=%s (%d matchup(s))",
        canonical_league_id,
        season,
        week,
        len(highlights.get("matchups", [])),
    )
    _throttle()
    recap = generate_recap(highlights)
    try:
        _table.put_item(
            Item={
                "PK": f"LEAGUE#{canonical_league_id}",
                "SK": f"MATCHUP_RECAP#{season}#WEEK#{week}",
                "data": [
                    {
                        "headline": recap["headline"],
                        "body": recap["body"],
                        "generated_at": _now_iso(),
                        "model": _MODEL_ID,
                    }
                ],
            },
            ConditionExpression="attribute_not_exists(SK)",
        )
        logger.info(
            "Wrote recap for league=%s season=%s week=%s: %r",
            canonical_league_id,
            season,
            week,
            recap["headline"],
        )
        return True
    except ClientError as exc:
        if (
            exc.response.get("Error", {}).get("Code")
            == "ConditionalCheckFailedException"
        ):
            logger.info(
                "Recap already present for league=%s season=%s week=%s; skipping write",
                canonical_league_id,
                season,
                week,
            )
            return False  # already written — idempotent
        raise


def _throttle() -> None:
    """Sleep so consecutive generations stay under ``RECAP_MAX_RPM``."""
    global _last_call_monotonic
    if _MIN_INTERVAL_S > 0:
        wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call_monotonic)
        if wait > 0:
            time.sleep(wait)
    _last_call_monotonic = time.monotonic()


# --- Queue markers ---------------------------------------------------------------


def _get_pending_markers() -> list[dict]:
    """Every ``PENDING#`` marker in the recap queue partition."""
    markers: list[dict] = []
    kwargs = {
        "KeyConditionExpression": Key("PK").eq(_QUEUE_PK)
        & Key("SK").begins_with("PENDING#"),
    }
    while True:
        resp = _table.query(**kwargs)
        markers.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return markers


def _delete_marker(canonical_league_id: str) -> None:
    _table.delete_item(Key={"PK": _QUEUE_PK, "SK": f"PENDING#{canonical_league_id}"})


# --- View reads ------------------------------------------------------------------


def _convert_decimals(obj):
    """Recursively convert DynamoDB ``Decimal``s to JSON-friendly int/float."""
    if isinstance(obj, list):
        return [_convert_decimals(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def _get_metadata(canonical_league_id: str) -> dict:
    resp = _table.get_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"}
    )
    return resp.get("Item", {})


def _is_subscription_active(metadata: dict) -> bool:
    """True while ``now < subscription_end_time`` (mirrors BE-014's comparison)."""
    end_time = metadata.get("subscription_end_time")
    if not end_time:
        return False
    end = _parse_iso(end_time)
    if end is None:
        return False
    return _now() < end


def _get_league_seasons(canonical_league_id: str) -> list[str]:
    """All seasons the league has, via the GSI1 LEAGUE_LOOKUP index (merged sets)."""
    resp = _table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("canonical_league_id").eq(canonical_league_id),
    )
    seasons: set[str] = set()
    for item in resp.get("Items", []):
        seasons.update(item.get("seasons", set()))
    return sorted(seasons)


def _get_matchup_weeks(canonical_league_id: str, season: str) -> dict[str, list]:
    """Return ``{week2: matchups}`` for every completed week of a season."""
    weeks: dict[str, list] = {}
    kwargs = {
        "KeyConditionExpression": Key("PK").eq(f"LEAGUE#{canonical_league_id}")
        & Key("SK").begins_with(f"MATCHUPS#{season}#"),
    }
    while True:
        resp = _table.query(**kwargs)
        for item in resp.get("Items", []):
            week2 = item["SK"].split("#")[-1]
            weeks[week2] = _convert_decimals(item.get("data", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return weeks


def _get_standings(canonical_league_id: str, season: str) -> dict[str, dict]:
    """Return ``{team_id: standings_row}`` for the season's **final** standings.

    Used as the per-week fallback for weeks with no ``WEEKLY_STANDINGS`` snapshot
    (e.g. playoff weeks); regular-season weeks use :func:`_get_weekly_standings`.
    """
    resp = _table.get_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": f"STANDINGS#{season}"}
    )
    rows = _convert_decimals(resp.get("Item", {}).get("data", []))
    return {str(row.get("team_id")): row for row in rows}


def _get_weekly_standings(
    canonical_league_id: str, season: str
) -> dict[int, dict[str, dict]]:
    """Return ``{snapshot_week: {team_id: standings_row}}`` from ``WEEKLY_STANDINGS``.

    Each row's ``record`` is the team's cumulative record **through that week**, so a
    week's recap can show the standings as they were at the time — not the end-of-season
    record. ``snapshot_week`` covers regular-season weeks only.
    """
    resp = _table.get_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": f"WEEKLY_STANDINGS#{season}"}
    )
    rows = _convert_decimals(resp.get("Item", {}).get("data", []))
    by_week: dict[int, dict[str, dict]] = {}
    for row in rows:
        week = _week_int(row.get("snapshot_week"))
        if week is None:
            continue
        by_week.setdefault(week, {})[str(row.get("team_id"))] = row
    return by_week


def _week_int(value) -> int | None:
    """Parse a week label (``"7"`` or zero-padded ``"07"``) to an int, or ``None``."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _parse_iso(value) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":  # pragma: no cover
    main()
