"""AI weekly matchup recap drainer — scheduled Lambda for LeagueQL (BE-022).

Runs on an EventBridge cron. Each tick it drains the ``RECAP_QUEUE`` partition:
for every pending league it premium-gates, enumerates every season's completed weeks,
drops already-recapped weeks, builds the matchup highlights, and turns each missing
``(season, week)`` into a Bedrock **batch inference** input record. It aggregates the
records **across all pending leagues** into one JSONL in S3 and submits a single
``CreateModelInvocationJob`` — so generation runs on batch's separate quota lane
rather than the very low real-time RPM quota.

Aggregating clears Bedrock's minimum-records-per-job floor: if the accumulated record
count is below ``RECAP_MIN_BATCH_RECORDS`` the drainer submits nothing this tick and
leaves the markers, so work piles up until a later tick clears the floor. When it does
submit, it writes a ``RECAP_JOB`` manifest (recordId → ``(league, season, week)``) and
flips the contributing leagues' markers to ``in_flight``; the recap-completion Lambda
(BE-022) consumes the manifest when the job finishes. Generation is idempotent —
already-recapped weeks are excluded before records are built — so re-drains are cheap.
"""

import datetime
import json
import os
import uuid
from decimal import Decimal

import boto3
import botocore.config
from boto3.dynamodb.conditions import Key

from common.bedrock import build_recap_record, submit_batch_job
from common.feature_flags import (
    PREMIUM_FEATURE,
    is_billing_enabled,
    is_feature_paywalled,
)
from common.logging_utils import correlation_id_var, logger
from common.tracing import init_tracing, traced_handler

# Roots its own trace (no upstream carrier): the drainer batches many leagues into one
# job, so it cannot continue any single trigger's span (BE-021). A no-op unless Axiom
# is configured.
init_tracing("leagueql-recap-drainer")

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_table_name = os.environ["DYNAMODB_TABLE_NAME"]
_table = boto3.resource("dynamodb", config=_retry_config).Table(_table_name)
_s3 = boto3.client("s3", config=_retry_config)

_QUEUE_PK = "RECAP_QUEUE"

# Minimum number of records before a batch job is submitted (Bedrock's per-job floor).
# Below this the drainer holds the markers and waits for more work to accumulate.
_MIN_BATCH_RECORDS = int(os.environ.get("RECAP_MIN_BATCH_RECORDS", "100"))

# An ``in_flight`` marker older than this (job vanished / no terminal event) is treated
# as pending and resubmitted. The idempotent recap write makes a double generation
# harmless (wasted spend at worst).
_STALE_INFLIGHT_HOURS = float(os.environ.get("RECAP_STALE_INFLIGHT_HOURS", "6"))

# How many top performers from each side to include in the highlights, trimmed to keep
# the prompt's input tokens low.
_TOP_STARTERS = 2
_TOP_BENCH = 1


def lambda_handler(event, context):  # pragma: no cover - thin entrypoint
    """EventBridge cron entrypoint. Roots a fresh trace and drains the queue."""
    with traced_handler("recap_drainer.handle", root=True):
        result = _handle()
    logger.info("Recap drainer finished: %s", result)
    return result


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _handle() -> dict:
    if not is_billing_enabled():
        logger.info("Billing disabled; recap drainer skipped")
        return {"status": "skipped", "reason": "billing_disabled"}

    markers = _get_drainable_markers()
    if not markers:
        logger.info("No pending recap work")
        return {"status": "completed", "submitted": 0, "records": 0}

    model_id = os.environ["BEDROCK_MODEL_ID"]
    records: list[
        tuple[str, str, str, str, dict]
    ] = []  # (record_id, league, season, week, highlights)
    contributing: list[str] = []
    for marker in markers:
        canonical_league_id = marker["canonical_league_id"]
        correlation_id_var.set(marker.get("correlation_id") or "")
        league_records = _league_records(canonical_league_id)
        if league_records is None:
            # Non-premium: gate already deleted the marker. No records, no spend.
            continue
        if not league_records:
            # Premium but every completed week is already recapped — done; clear it.
            _delete_marker(canonical_league_id)
            continue
        records.extend(league_records)
        contributing.append(canonical_league_id)

    if not records:
        logger.info("No missing weeks across pending leagues")
        return {"status": "completed", "submitted": 0, "records": 0}

    if len(records) < _MIN_BATCH_RECORDS:
        logger.info(
            "Pending recap work (%d records) below the batch minimum (%d); holding",
            len(records),
            _MIN_BATCH_RECORDS,
        )
        return {"status": "held", "submitted": 0, "records": len(records)}

    job_arn = _submit(records, contributing, model_id)
    logger.info(
        "Submitted recap batch job %s: %d record(s) across %d league(s)",
        job_arn,
        len(records),
        len(contributing),
    )
    return {
        "status": "submitted",
        "submitted": 1,
        "records": len(records),
        "leagues": len(contributing),
        "job_arn": job_arn,
    }


def _submit(
    records: list[tuple[str, str, str, str, dict]],
    contributing: list[str],
    model_id: str,
) -> str:
    """Write the input JSONL to S3, submit the batch job, write the manifest, flip
    the contributing markers to ``in_flight``. Returns the job ARN."""
    bucket = os.environ["RECAP_BATCH_BUCKET"]
    role_arn = os.environ["RECAP_BATCH_ROLE_ARN"]
    job_name = (
        f"leagueql-recap-{_now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    )

    lines = []
    routing: dict[str, dict] = {}
    for record_id, league, season, week, highlights in records:
        lines.append(json.dumps(build_recap_record(record_id, highlights)))
        routing[record_id] = {
            "canonical_league_id": league,
            "season": season,
            "week": week,
        }

    input_key = f"input/{job_name}.jsonl"
    _s3.put_object(
        Bucket=bucket, Key=input_key, Body=("\n".join(lines) + "\n").encode("utf-8")
    )
    input_uri = f"s3://{bucket}/{input_key}"
    output_uri = f"s3://{bucket}/output/{job_name}/"

    job_arn = submit_batch_job(
        job_name=job_name,
        input_uri=input_uri,
        output_uri=output_uri,
        role_arn=role_arn,
    )

    submitted_at = _now_iso()
    _table.put_item(
        Item={
            "PK": f"RECAP_JOB#{job_arn}",
            "SK": "MANIFEST",
            "job_name": job_name,
            "output_uri": output_uri,
            "model": model_id,
            "league_ids": contributing,
            "records": routing,
            "submitted_at": submitted_at,
        }
    )
    for league in contributing:
        _mark_in_flight(league, job_arn, submitted_at)
    return job_arn


def _league_records(
    canonical_league_id: str,
) -> list[tuple[str, str, str, str, dict]] | None:
    """Build the batch records for a league's missing weeks.

    Returns ``None`` when the league is gated out (non-premium — marker deleted, no
    spend), otherwise the (possibly empty) list of ``(record_id, league, season,
    week, highlights)`` tuples for weeks that do not yet have a recap.
    """
    metadata = _get_metadata(canonical_league_id)
    if is_feature_paywalled(PREMIUM_FEATURE) and not _is_subscription_active(metadata):
        logger.info(
            "League %s has no active subscription; dropping from recap queue",
            canonical_league_id,
        )
        _delete_marker(canonical_league_id)
        return None

    records: list[tuple[str, str, str, str, dict]] = []
    for season in _get_league_seasons(canonical_league_id):
        weeks = _get_matchup_weeks(canonical_league_id, season)
        if not weeks:
            continue
        standings = _get_standings(canonical_league_id, season)
        existing = _get_existing_recap_weeks(canonical_league_id, season)
        for week, matchups in weeks.items():
            if week in existing:
                continue
            highlights = _build_highlights(season, week, matchups, standings)
            records.append(
                (uuid.uuid4().hex, canonical_league_id, season, week, highlights)
            )
    return records


# --- Queue markers ---------------------------------------------------------------


def _get_drainable_markers() -> list[dict]:
    """Pending markers, plus ``in_flight`` markers stale past the reset threshold."""
    cutoff = _now() - datetime.timedelta(hours=_STALE_INFLIGHT_HOURS)
    markers: list[dict] = []
    kwargs = {"KeyConditionExpression": Key("PK").eq(_QUEUE_PK)}
    while True:
        resp = _table.query(**kwargs)
        for item in resp.get("Items", []):
            if item.get("status") == "in_flight":
                submitted_at = _parse_iso(item.get("submitted_at"))
                if submitted_at is not None and submitted_at >= cutoff:
                    continue  # job still in flight within the threshold
                logger.warning(
                    "Resubmitting stale in-flight recap marker for league=%s",
                    item.get("canonical_league_id"),
                )
            markers.append(item)
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return markers


def _delete_marker(canonical_league_id: str) -> None:
    _table.delete_item(Key={"PK": _QUEUE_PK, "SK": f"PENDING#{canonical_league_id}"})


def _mark_in_flight(canonical_league_id: str, job_arn: str, submitted_at: str) -> None:
    _table.update_item(
        Key={"PK": _QUEUE_PK, "SK": f"PENDING#{canonical_league_id}"},
        UpdateExpression="SET #s = :inflight, job_id = :job, submitted_at = :ts",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":inflight": "in_flight",
            ":job": job_arn,
            ":ts": submitted_at,
        },
    )


# --- View reads (shared shape with the old generator) ----------------------------


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


def _parse_iso(value) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
