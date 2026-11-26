"""Nightly unused-league reaper Lambda for LeagueQL (backend/league-reaper).

Runs on an EventBridge schedule (09:00 UTC daily, prod-only) and permanently removes
leagues that nobody has opened for a calendar year: their raw S3 payloads, every DynamoDB
item, and any platform credentials the removal orphans. Only the primary region is written;
S3 delete markers and global-table deletes replicate to the other one.

It is a **dry run** (reads only) unless ``LEAGUE_REAPER_DRY_RUN`` is exactly ``false``.
Whenever leagues are eligible it posts a summary to the admin Discord channel through the
same webhook as the onboarding report.

Raw S3 data is deleted before DynamoDB, and METADATA goes last, so a partially removed
league stays in GSI3 and the next run retries it.
"""

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from eligibility import is_expired, last_activity

from common import league_deletion
from common.aws import RETRY_CONFIG
from common.http import build_retry_session
from common.logging_utils import logger
from common.secrets import get_secret_from_env_param

GSI3_INDEX_NAME = "GSI3"
# Don't start another removal with less execution time than this left, so the Lambda
# timeout can't cut one off mid-way.
TIME_FLOOR_MS = 60_000
# Discord caps an embed description at 4,096 characters; leave room for the "+N more" line.
_MAX_DESCRIPTION_CHARS = 4000

_COLOR_ORANGE = 0xE67E22
_COLOR_RED = 0xE74C3C

_TABLE = boto3.resource("dynamodb", config=RETRY_CONFIG).Table(
    os.environ["DYNAMODB_TABLE_NAME"]
)
_S3 = boto3.client("s3", config=RETRY_CONFIG)
_BUCKET = os.environ["S3_BUCKET_NAME"]

# Webhook URL resolved once per cold start from its SSM parameter name.
_WEBHOOK_URL = get_secret_from_env_param("DISCORD_WEBHOOK_URL_SSM_PARAM")

_session = build_retry_session()


@dataclass
class RunResult:
    """What one reaper run did (or, in a dry run, would do)."""

    removed: list[dict] = field(default_factory=list)
    skipped: int = 0
    failed: list[str] = field(default_factory=list)
    cleanup_failed: list[str] = field(default_factory=list)
    deferred: int = 0

    @property
    def has_findings(self) -> bool:
        return bool(self.removed or self.skipped or self.failed or self.deferred)


def _is_dry_run() -> bool:
    """Only an explicit ``false`` enables deletion."""
    return os.environ.get("LEAGUE_REAPER_DRY_RUN", "").lower() != "false"


def _canonical_id(item: dict) -> str:
    return item["PK"].removeprefix("LEAGUE#")


def _effective_platform(metadata: dict) -> str | None:
    return metadata.get("active_platform") or metadata.get("platform")


def _find_candidates(now: datetime) -> list[str]:
    """Return the canonical ids GSI3 lists as expired (paginated)."""
    candidates: list[str] = []
    kwargs: dict[str, Any] = {
        "IndexName": GSI3_INDEX_NAME,
        "KeyConditionExpression": Key("SK").eq("METADATA"),
    }
    while True:
        response = _TABLE.query(**kwargs)
        candidates.extend(
            _canonical_id(item)
            for item in response.get("Items", [])
            if is_expired(item, now)
        )
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return candidates
        kwargs["ExclusiveStartKey"] = last_key


def _get_item(pk: str, sk: str) -> dict | None:
    return _TABLE.get_item(Key={"PK": pk, "SK": sk}, ConsistentRead=True).get("Item")


def _busy_reason(metadata: dict, now: datetime) -> str | None:
    """Return why a league must not be touched right now, or ``None``."""
    if metadata.get("lineup_backfill_lease_until", 0) > now.timestamp():
        return "lineup backfill running"
    job_id = metadata.get("active_job_id")
    if job_id:
        job = _get_item(f"JOB#{job_id}", "JOB_STATUS")
        if job and job.get("status") == "IN_PROGRESS":
            return "job in progress"
    return None


def _remove_orphaned_credentials(metadata: dict, removed_ids: set[str]) -> None:
    """Delete the owner's platform credentials if no remaining league needs them.

    Same rules as a manual delete (backend/delete-league). ``removed_ids`` holds every
    league removed so far this run, so a lagging GSI3 can't keep credentials alive when
    one owner loses several leagues.
    """
    owner = metadata.get("owner_user_id")
    if not owner:
        return
    platform = _effective_platform(metadata)
    if platform == "YAHOO":
        sk, still_needed = "YAHOO_OAUTH", league_deletion.owner_has_other_yahoo_leagues
    elif platform == "ESPN":
        sk = "ESPN_CREDENTIALS"
        still_needed = league_deletion.owner_has_other_optedin_espn_leagues
    else:
        return
    if not still_needed(_TABLE, owner, removed_ids):
        _TABLE.delete_item(Key={"PK": f"USER#{owner}", "SK": sk})
        logger.info("Removed orphaned %s item for an unused league's owner", sk)


def _describe(canonical_league_id: str, metadata: dict) -> dict:
    activity = last_activity(metadata)
    return {
        "canonical_league_id": canonical_league_id,
        "league_name": metadata.get("league_name") or "(unnamed)",
        "platform": _effective_platform(metadata) or "UNKNOWN",
        "last_activity": f"{activity:%Y-%m-%d}",
    }


def _process_league(
    canonical_league_id: str,
    now: datetime,
    dry_run: bool,
    removed_ids: set[str],
    result: RunResult,
) -> None:
    """Re-check one candidate against its current METADATA and remove it if still idle."""
    metadata = _get_item(f"LEAGUE#{canonical_league_id}", "METADATA")
    if metadata is None or not is_expired(metadata, now):
        logger.info("League %s is no longer eligible", canonical_league_id)
        return
    reason = _busy_reason(metadata, now)
    if reason:
        logger.info("Skipping league %s: %s", canonical_league_id, reason)
        result.skipped += 1
        return

    league = _describe(canonical_league_id, metadata)
    # The log is the full record: the Discord summary may be truncated.
    logger.info(
        "%s unused league: %s", "Would remove" if dry_run else "Removing", league
    )
    if dry_run:
        result.removed.append(league)
        return

    league_deletion.delete_league_raw_data(_S3, _BUCKET, canonical_league_id)
    league_deletion.delete_all_league_items(_TABLE, canonical_league_id)
    removed_ids.add(canonical_league_id)
    result.removed.append(league)

    try:
        _remove_orphaned_credentials(metadata, removed_ids)
    except Exception:  # noqa: BLE001 — the league is already gone
        logger.exception("Credential cleanup failed for %s", canonical_league_id)
        result.cleanup_failed.append(canonical_league_id)


def _run(context: Any, now: datetime, dry_run: bool) -> RunResult:
    result = RunResult()
    removed_ids: set[str] = set()
    candidates = _find_candidates(now)
    for index, canonical_league_id in enumerate(candidates):
        if context.get_remaining_time_in_millis() < TIME_FLOOR_MS:
            result.deferred = len(candidates) - index
            logger.warning("Out of time; deferring %d leagues", result.deferred)
            break
        try:
            _process_league(canonical_league_id, now, dry_run, removed_ids, result)
        except Exception:  # noqa: BLE001 — isolate one league's failure
            logger.exception("Failed to remove league %s", canonical_league_id)
            result.failed.append(canonical_league_id)
    return result


def _build_description(lines: list[str]) -> str:
    """Join the league lines, cutting off with "+N more" at Discord's size limit."""
    shown: list[str] = []
    length = 0
    for line in lines:
        length += len(line) + 1
        if length > _MAX_DESCRIPTION_CHARS:
            shown.append(f"+{len(lines) - len(shown)} more")
            break
        shown.append(line)
    return "\n".join(shown)


def _build_embed(result: RunResult, dry_run: bool, now: datetime) -> dict:
    # Problems go first so that truncating a long list never hides them.
    lines = [f"❌ Failed: `{cid}`" for cid in result.failed]
    lines += [f"⚠️ Credential cleanup failed: `{cid}`" for cid in result.cleanup_failed]
    lines += [
        f"• {league['league_name']} ({league['platform']}) "
        f"`{league['canonical_league_id']}` last active {league['last_activity']}"
        for league in result.removed
    ]
    counts = [
        ("Would remove" if dry_run else "Removed", len(result.removed)),
        ("Skipped (busy)", result.skipped),
        ("Failed", len(result.failed)),
        ("Deferred", result.deferred),
    ]
    mode = "DRY RUN (nothing deleted)" if dry_run else "Removed unused leagues"
    return {
        "title": f"🧹 LeagueQL league reaper: {mode}",
        "color": _COLOR_RED if result.failed else _COLOR_ORANGE,
        "description": _build_description(lines),
        "fields": [
            {"name": name, "value": f"{value:,}", "inline": True}
            for name, value in counts
        ],
        "footer": {"text": f"Generated {now:%Y-%m-%d %H:%M} UTC"},
    }


def _post_to_discord(embed: dict) -> None:
    """POST a single embed to the Discord webhook, raising on a non-2xx response."""
    response = _session.post(_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
    response.raise_for_status()


def lambda_handler(event, context) -> None:
    """Scheduled entry point: remove (or report) unused leagues.

    Raises:
        RuntimeError: If the webhook isn't configured (before anything is removed), or if
            any league failed, so the Lambda's error alarm fires. Removal is idempotent,
            so retries are safe.
    """
    if not _WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL_SSM_PARAM unset; not running the reaper")
        raise RuntimeError("Discord webhook URL is not configured")

    dry_run = _is_dry_run()
    now = datetime.now(UTC)
    logger.info("Starting league reaper (dry_run=%s)", dry_run)
    result = _run(context, now, dry_run)
    logger.info(
        "Reaper finished: removed=%d skipped=%d failed=%d deferred=%d dry_run=%s",
        len(result.removed),
        result.skipped,
        len(result.failed),
        result.deferred,
        dry_run,
    )

    if result.has_findings:
        _post_to_discord(_build_embed(result, dry_run, now))
    if result.failed:
        raise RuntimeError(f"Failed to remove {len(result.failed)} unused leagues")
