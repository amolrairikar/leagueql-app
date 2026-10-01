"""Yahoo lineup backfill (backend/yahoo-lineup-backfill).

Yahoo onboards/refreshes skip per-team weekly rosters (only the single-team roster call returns
weekly player points, and fetching it for every team and week trips Yahoo's ``999`` throttle).
Instead they mark the league's seasons lineup-pending on METADATA and queue a message here.

Each SQS message ``{"canonical_league_id", "attempt"}`` runs one paced pass over the league's
newest lineup-pending season:

1. Take a time-limited lease on METADATA so only one run per league is ever active.
2. Fetch each team's roster + weekly points for the season's finished weeks that are not already
   in the season's lineup store (``raw-api-data/{id}/yahoo_rosters/{season}.json``), one request
   at a time, checkpointing the store after every week.
3. On completion, re-trigger the processor for just that season (self-copy of ``manifest.json``
   with ``reprocess_seasons`` metadata), drop the season from ``pending_lineup_seasons`` and chain
   the next pending season. On a ``999`` stop at once and retry ~15 minutes later; after
   ``MAX_ATTEMPTS`` throttled attempts the season moves to ``failed_lineup_seasons`` (the next
   weekly refresh re-queues it).

Deployed as a second Lambda from the onboarder package so it reuses the Yahoo roster
URL/parsing, the writer's AWS clients, and the shared token engine.
"""

import json
import os
import time
import uuid
from typing import Any

import boto3
import botocore.config
import botocore.exceptions
import requests
from utils import correlation_id_var, logger
from writer import send_lineup_backfill_message
from yahoo_client import parse_team_roster, team_roster_url

from common.tracing import init_tracing, inject_context, traced_handler
from common.yahoo_tokens import YahooReauthRequired
from common.yahoo_tokens import from_env as yahoo_tokens_from_env

init_tracing("leagueql-lineup-backfill")

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_s3 = boto3.client("s3", config=_retry_config)
_dynamodb = boto3.client("dynamodb", config=_retry_config)

# A run holds the league lease this long; longer than the Lambda timeout (900s) so a live run
# never loses it, short enough that a crashed run's lease frees itself.
LEASE_SECONDS = 15 * 60
# Throttled retries wait SQS's maximum per-message delay.
RETRY_DELAY_SECONDS = 900
# Consecutive throttled attempts on one season before it is marked failed (~2h of retries).
MAX_ATTEMPTS = 8
# Stop and re-queue (progress is checkpointed) when less than this much Lambda time remains.
TIME_BUDGET_FLOOR_MS = 60_000
YAHOO_THROTTLED_STATUS = 999
PERMANENT_STATUSES = {401, 403, 404}


class YahooThrottled(Exception):
    """Yahoo returned ``999 Request denied``."""


class PermanentBackfillError(Exception):
    """The season can't be backfilled until something changes (revoked link, no access)."""


class OutOfTime(Exception):
    """The Lambda is close to its timeout; progress is saved and the run re-queued."""


def _request_interval() -> float:
    """Seconds between Yahoo requests (paced well under Yahoo's throttle)."""
    return float(os.environ.get("LINEUP_BACKFILL_REQUEST_INTERVAL", "1.0"))


def _metadata_key(canonical_league_id: str) -> dict[str, Any]:
    return {"PK": {"S": f"LEAGUE#{canonical_league_id}"}, "SK": {"S": "METADATA"}}


def _table() -> str:
    return os.environ["DYNAMODB_TABLE_NAME"]


def _bucket() -> str:
    return os.environ["S3_BUCKET_NAME"]


# --------------------------------------------------------------------------------------
# METADATA: lease + pending/failed bookkeeping
# --------------------------------------------------------------------------------------
def _get_metadata(canonical_league_id: str) -> dict[str, Any] | None:
    response = _dynamodb.get_item(
        TableName=_table(), Key=_metadata_key(canonical_league_id), ConsistentRead=True
    )
    return response.get("Item")


def _acquire_lease(canonical_league_id: str) -> int | None:
    """Take the league's backfill lease; return its expiry, or None if another run holds it."""
    now = int(time.time())
    lease_until = now + LEASE_SECONDS
    try:
        _dynamodb.update_item(
            TableName=_table(),
            Key=_metadata_key(canonical_league_id),
            UpdateExpression="SET lineup_backfill_lease_until = :until",
            ConditionExpression=(
                "attribute_exists(PK) AND (attribute_not_exists(lineup_backfill_lease_until)"
                " OR lineup_backfill_lease_until < :now)"
            ),
            ExpressionAttributeValues={
                ":until": {"N": str(lease_until)},
                ":now": {"N": str(now)},
            },
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return None
        raise
    return lease_until


def _release_lease(canonical_league_id: str, lease_until: int) -> None:
    """Release our lease (only if it is still ours — an expired lease may have been retaken)."""
    try:
        _dynamodb.update_item(
            TableName=_table(),
            Key=_metadata_key(canonical_league_id),
            UpdateExpression="REMOVE lineup_backfill_lease_until",
            ConditionExpression="lineup_backfill_lease_until = :mine",
            ExpressionAttributeValues={":mine": {"N": str(lease_until)}},
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        logger.warning("Lineup backfill lease for %s was retaken", canonical_league_id)


def _mark_complete(canonical_league_id: str, season: str) -> None:
    _dynamodb.update_item(
        TableName=_table(),
        Key=_metadata_key(canonical_league_id),
        UpdateExpression="DELETE pending_lineup_seasons :s",
        ExpressionAttributeValues={":s": {"SS": [season]}},
    )


def _mark_failed(canonical_league_id: str, season: str) -> None:
    _dynamodb.update_item(
        TableName=_table(),
        Key=_metadata_key(canonical_league_id),
        UpdateExpression="DELETE pending_lineup_seasons :s ADD failed_lineup_seasons :s",
        ExpressionAttributeValues={":s": {"SS": [season]}},
    )


# --------------------------------------------------------------------------------------
# S3: season raw data, lineup store, processor trigger
# --------------------------------------------------------------------------------------
def _read_json(key: str) -> Any | None:
    try:
        response = _s3.get_object(Bucket=_bucket(), Key=key)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise
    return json.loads(response["Body"].read())


def lineup_store_key(canonical_league_id: str, season: str) -> str:
    return f"raw-api-data/{canonical_league_id}/yahoo_rosters/{season}.json"


def _write_store(canonical_league_id: str, season: str, store: dict) -> None:
    _s3.put_object(
        Bucket=_bucket(),
        Key=lineup_store_key(canonical_league_id, season),
        Body=json.dumps(store),
        ContentType="application/json",
    )


def completed_weeks(season_records: list[dict]) -> dict[str, list[str]]:
    """Map each finished week to its team keys, from the season's stored scoreboards.

    A week counts as finished only when every one of its matchups is ``postevent``.
    """
    weeks: dict[str, dict[str, Any]] = {}
    for record in season_records:
        if not str(record.get("data_type", "")).startswith("matchups_week"):
            continue
        for matchup in (record.get("data") or {}).get("matchups", []):
            week = str(matchup.get("week"))
            entry = weeks.setdefault(week, {"finished": True, "teams": set()})
            entry["finished"] &= matchup.get("status") == "postevent"
            entry["teams"].update(
                t["team_key"] for t in matchup.get("teams", []) if t.get("team_key")
            )
    return {
        week: sorted(entry["teams"])
        for week, entry in weeks.items()
        if entry["finished"] and entry["teams"]
    }


def _publish_season(canonical_league_id: str, season: str) -> None:
    """Have the processor rebuild just ``season`` (backend/data-processing-pipeline).

    Copying the manifest onto itself fires its ``ObjectCreated`` trigger with new metadata. S3
    copies the *current* body server-side, so a refresh that updated the manifest concurrently
    is never overwritten with a stale copy.
    """
    key = f"raw-api-data/{canonical_league_id}/manifest.json"
    metadata = inject_context({"reprocess_seasons": season})
    _s3.copy_object(
        Bucket=_bucket(),
        Key=key,
        CopySource={"Bucket": _bucket(), "Key": key},
        MetadataDirective="REPLACE",
        Metadata=metadata,
        ContentType="application/json",
    )


# --------------------------------------------------------------------------------------
# Yahoo fetch
# --------------------------------------------------------------------------------------
class _YahooFetcher:
    """Sequential, paced Yahoo GETs with the owner's (auto-refreshed) token."""

    def __init__(self, owner_user_id: str):
        self._token_client = yahoo_tokens_from_env()
        self._owner = owner_user_id
        self._last_request = 0.0

    def _token(self) -> str:
        try:
            return self._token_client.get_valid_access_token(self._owner)
        except YahooReauthRequired as e:
            raise PermanentBackfillError("Yahoo link revoked") from e

    def _pace(self) -> None:
        wait = _request_interval() - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _send(self, url: str) -> requests.Response:
        self._pace()
        return requests.get(
            url, headers={"Authorization": f"Bearer {self._token()}"}, timeout=30
        )

    def get(self, url: str) -> dict:
        response = self._send(url)
        # A 401 means the token expired mid-run; the engine hands out a fresh one on retry.
        if response.status_code == 401:
            response = self._send(url)
        if response.status_code == YAHOO_THROTTLED_STATUS:
            raise YahooThrottled(url)
        if response.status_code in PERMANENT_STATUSES:
            raise PermanentBackfillError(f"HTTP {response.status_code} for {url}")
        response.raise_for_status()
        return response.json()


def backfill_season(
    canonical_league_id: str, season: str, owner_user_id: str, lambda_context: Any
) -> None:
    """Fetch every finished, not-yet-stored week of ``season`` into its lineup store."""
    season_records = (
        _read_json(f"raw-api-data/{canonical_league_id}/{season}.json") or []
    )
    store = _read_json(lineup_store_key(canonical_league_id, season)) or {"weeks": {}}
    weeks = completed_weeks(season_records)
    missing = sorted((w for w in weeks if w not in store["weeks"]), key=int)
    logger.info(
        "Lineup backfill: canonical_league_id=%s season=%s finished_weeks=%d to_fetch=%s",
        canonical_league_id,
        season,
        len(weeks),
        missing,
    )
    if not missing:
        return
    fetcher = _YahooFetcher(owner_user_id)
    for week in missing:
        if lambda_context.get_remaining_time_in_millis() < TIME_BUDGET_FLOOR_MS:
            raise OutOfTime(f"stopped before week {week}")
        rows: list[dict] = []
        for team_key in weeks[week]:
            rows.extend(
                parse_team_roster(fetcher.get(team_roster_url(team_key, week)), week)
            )
        store["weeks"][week] = rows
        # Checkpoint every week so a throttled/timed-out run resumes where it stopped.
        _write_store(canonical_league_id, season, store)


# --------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------
def _newest(seasons: set[str] | list[str]) -> str:
    return max(seasons, key=int)


def run_backfill(canonical_league_id: str, attempt: int, lambda_context: Any) -> str:
    """Run one backfill pass for a league; returns an outcome label (for logs/tests)."""
    metadata = _get_metadata(canonical_league_id)
    if metadata is None:
        logger.info(
            "League %s no longer exists; dropping backfill", canonical_league_id
        )
        return "league_missing"
    lease_until = _acquire_lease(canonical_league_id)
    if lease_until is None:
        logger.info("Lineup backfill already running for %s", canonical_league_id)
        return "lease_held"
    try:
        pending = metadata.get("pending_lineup_seasons", {}).get("SS", [])
        if not pending:
            return "nothing_pending"
        season = _newest(pending)
        owner = metadata.get("owner_user_id", {}).get("S")
        try:
            if not owner:
                raise PermanentBackfillError("league has no owner to authorize Yahoo")
            backfill_season(canonical_league_id, season, owner, lambda_context)
        except YahooThrottled as e:
            return _handle_throttle(canonical_league_id, season, pending, attempt, e)
        except PermanentBackfillError as e:
            logger.error(
                "Lineup backfill failed permanently: canonical_league_id=%s season=%s %s",
                canonical_league_id,
                season,
                e,
            )
            _mark_failed(canonical_league_id, season)
            return "failed"
        except OutOfTime:
            send_lineup_backfill_message(canonical_league_id, attempt=attempt)
            return "out_of_time"

        _publish_season(canonical_league_id, season)
        _mark_complete(canonical_league_id, season)
        logger.info(
            "Lineup backfill completed: canonical_league_id=%s season=%s",
            canonical_league_id,
            season,
        )
        if set(pending) - {season}:
            send_lineup_backfill_message(canonical_league_id)
        return "completed"
    finally:
        _release_lease(canonical_league_id, lease_until)


def _handle_throttle(
    canonical_league_id: str,
    season: str,
    pending: list[str],
    attempt: int,
    error: YahooThrottled,
) -> str:
    next_attempt = attempt + 1
    logger.warning(
        "Yahoo throttled lineup backfill: canonical_league_id=%s season=%s attempt=%d url=%s",
        canonical_league_id,
        season,
        next_attempt,
        error,
    )
    if next_attempt < MAX_ATTEMPTS:
        send_lineup_backfill_message(
            canonical_league_id, attempt=next_attempt, delay_seconds=RETRY_DELAY_SECONDS
        )
        return "throttled"
    _mark_failed(canonical_league_id, season)
    if set(pending) - {season}:
        send_lineup_backfill_message(
            canonical_league_id, delay_seconds=RETRY_DELAY_SECONDS
        )
    return "retries_exhausted"


def lambda_handler(event, context) -> dict[str, Any]:
    """SQS entry point (batch size 1): one backfill pass per message."""
    outcomes = []
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        canonical_league_id = body["canonical_league_id"]
        correlation_id_var.set(str(uuid.uuid4()))
        with traced_handler("lineup_backfill.handle", root=True):
            outcomes.append(
                run_backfill(canonical_league_id, int(body.get("attempt", 0)), context)
            )
    return {"outcomes": outcomes}
