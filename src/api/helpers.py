"""Helper functions for the LeagueQL API.

DynamoDB access, Sleeper NFL state, SNS alerting, and small data utilities.
Functions that touch the patched singleton ``table`` reach it through the ``main``
module at call time so tests can patch ``main.table`` and have it take effect here.
SNS failure alerting lives in the shared ``common.sns`` module.
"""

import time
from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal
from functools import partial
from typing import Any

import botocore.exceptions
import main
import requests as http_requests
from boto3.dynamodb.conditions import Attr, Key
from fastapi import HTTPException, status
from main import (
    SLEEPER_STATE_URL,
    logger,
)

from common.job_status import JOB_TTL_SECONDS
from common.sns import publish_failure as _publish_failure

# Binds the API's SNS subject; the shared implementation handles the no-op guard,
# correlation_id, and error swallowing.
publish_failure = partial(_publish_failure, subject="LeagueQL API Failure")


def convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def lookup_league(league_id: str, platform) -> str:
    """
    Utility function to lookup a given league.

    Args:
        league_id: The ID for the league.
        platform: The platform the league is on (e.g., ESPN, SLEEPER).

    Returns:
        The canonical league ID associated with that league.
    """
    pk = f"LEAGUE#{league_id}#PLATFORM#{platform.value}"
    sk = "LEAGUE_LOOKUP"
    try:
        response = main.table.get_item(Key={"PK": pk, "SK": sk})
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to look up league",
        )

    item = response.get("Item")
    if not item:
        logger.warning("League %s not found for %s platform", league_id, platform.value)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found",
        )

    if not item.get("canonical_league_id"):
        logger.error(
            "canonical_league_id not found in item for league %s on platform %s",
            league_id,
            platform.value,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return item["canonical_league_id"]


def get_league_metadata(canonical_league_id: str) -> dict:
    """
    Utility function to get league metadata for a given canonical league ID.

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A dictionary containing the league metadata.
    """
    pk = f"LEAGUE#{canonical_league_id}"
    sk = "METADATA"
    try:
        response = main.table.get_item(Key={"PK": pk, "SK": sk})
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )

    item = response.get("Item")
    if not item:
        logger.warning("League with canonical ID %s not found", canonical_league_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return item


def read_view(
    canonical_league_id: str,
    sk_base: str,
    suffix: str | None,
    *,
    use_prefix: bool,
) -> list[Any] | None:
    """
    Read a single precomputed view's rows for a league.

    A view is stored either as one item read by exact sort key (``use_prefix`` False)
    or as several items sharing an SK prefix whose ``data`` lists are concatenated in
    sort-key order across all result pages (``use_prefix`` True — used for chunked or
    multi-item views such as transactions and per-week matchups). The sort key is
    ``{sk_base}#{suffix}`` when a suffix is given, else ``{sk_base}#`` (a bare prefix
    for collection reads). This is the shared read behind ``query_league`` and
    ``export_league``.

    Args:
        canonical_league_id: The canonical league ID.
        sk_base: The sort-key base for the view (e.g. ``STANDINGS``, ``MATCHUPS``).
        suffix: The suffix appended after ``{sk_base}#`` (e.g. a season), or None.
        use_prefix: Whether to resolve via a paginated ``begins_with`` prefix scan
            (True) or an exact ``get_item`` (False).

    Returns:
        The concatenated ``data`` list, or None when no matching item exists.
    """
    pk = f"LEAGUE#{canonical_league_id}"
    sk = f"{sk_base}#{suffix}" if suffix is not None else f"{sk_base}#"
    try:
        if use_prefix:
            items: list[Any] = []
            kwargs: dict[str, Any] = {
                "KeyConditionExpression": Key("PK").eq(pk) & Key("SK").begins_with(sk),
            }
            while True:
                db_response = main.table.query(**kwargs)
                items.extend(db_response.get("Items", []))
                last_key = db_response.get("LastEvaluatedKey")
                if not last_key:
                    break
                kwargs["ExclusiveStartKey"] = last_key
            if not items:
                return None
            all_data: list[Any] = []
            for item in items:
                all_data.extend(item.get("data", []))
            return all_data
        db_response = main.table.get_item(Key={"PK": pk, "SK": sk}, ConsistentRead=True)
        item = db_response.get("Item")
        if not item:
            return None
        return item.get("data", [])
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )


def get_nfl_state() -> dict | None:
    """
    Fetches the current NFL state from Sleeper.

    Returns:
        The NFL state response (containing season_type, season, and week),
        or None if the request fails (fail-open so refresh stays available).
    """
    try:
        resp = http_requests.get(SLEEPER_STATE_URL, timeout=(5, 10))
        resp.raise_for_status()
        return resp.json()
    except Exception:  # noqa: BLE001 — best-effort guard; never block refresh on this
        logger.warning(
            "Failed to fetch NFL state; skipping refresh guard", exc_info=True
        )
        return None


def _week_is_played(week_data: Any) -> bool:
    """
    Return whether a stored matchup week has an actual played result.

    A week counts as played when any of its matchup rows has a positive score.
    ESPN pre-stores the entire season's schedule, so future, unplayed weeks are
    persisted as 0-0 rows (winner "TIE"); those are not played. A genuinely played
    fantasy matchup always has a positive score, so a score-based check is
    unambiguous (unlike ``winner``, which is "TIE" for a 0-0 unplayed week) and
    works for both ESPN and Sleeper.

    Args:
        week_data: The ``data`` list stored on a MATCHUPS# item (list of matchup
            rows, each with ``team_a_score`` / ``team_b_score``).

    Returns:
        True if any matchup row in the week has a positive score, else False.
    """
    for row in week_data or []:
        if (row.get("team_a_score") or 0) > 0 or (row.get("team_b_score") or 0) > 0:
            return True
    return False


def get_latest_stored_matchup(canonical_league_id: str) -> tuple[int, int] | None:
    """
    Finds the most recent *played* stored matchup week for a league.

    Matchups are keyed SK=MATCHUPS#{season}#WEEK#{week:02d}. Because season is
    4-digit and week is zero-padded, the lexicographically-largest MATCHUPS# SK
    is the latest stored season/week — but that is not necessarily the latest
    *played* week. ESPN stores the whole season's schedule up front, so future,
    unplayed weeks are persisted as 0-0 rows; taking the max SK would make an
    in-season ESPN league look permanently up to date. We therefore walk MATCHUPS#
    items newest-first (descending SK == descending season/week) and return the
    first week with an actual played result. Sleeper only ever stores played weeks,
    so its latest played week equals its latest stored week.

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A (season, week) tuple for the most recent *played* stored matchup, or None
        if the league has no played matchups stored.
    """
    query_kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(f"LEAGUE#{canonical_league_id}")
        & Key("SK").begins_with("MATCHUPS#"),
        "ScanIndexForward": False,
        # "data" is a DynamoDB reserved word, so alias it in the projection.
        "ProjectionExpression": "SK, #data",
        "ExpressionAttributeNames": {"#data": "data"},
    }
    try:
        while True:
            response = main.table.query(**query_kwargs)
            for item in response.get("Items", []):
                if not _week_is_played(item.get("data")):
                    continue
                # SK format: MATCHUPS#{season}#WEEK#{week}
                _, season, _, week = item["SK"].split("#")
                return int(season), int(week)
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                return None
            query_kwargs["ExclusiveStartKey"] = last_key
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )


def get_league_seasons(canonical_league_id: str) -> list[str]:
    """
    Uses GSI1 to find all seasons a league has been onboarded for.

    Queries all LEAGUE_LOOKUP items that share the given canonical_league_id
    (there may be multiple for Sleeper leagues) and merges their season sets.

    Args:
        canonical_league_id: The canonical league ID to look up.

    Returns:
        A sorted list of unique season strings (e.g. ["2022", "2023", "2025"]).
    """
    try:
        response = main.table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("canonical_league_id").eq(canonical_league_id),
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league seasons",
        )

    items = response.get("Items", [])
    if not items:
        logger.warning(
            "No LEAGUE_LOOKUP items found for canonical_league_id %s",
            canonical_league_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    seasons: set[str] = set()
    for item in items:
        seasons.update(item.get("seasons", set()))

    return sorted(seasons)


def _query_all_keys(query_kwargs: dict) -> list[dict]:
    """
    Run a paginated query, returning every matched item's {PK, SK} key.

    Args:
        query_kwargs: Keyword arguments passed to table.query (must project PK/SK).

    Returns:
        A list of {"PK", "SK"} key dicts across all result pages.
    """
    keys: list[dict] = []
    kwargs = dict(query_kwargs)
    while True:
        response = main.table.query(**kwargs)
        for item in response.get("Items", []):
            keys.append({"PK": item["PK"], "SK": item["SK"]})
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return keys
        kwargs["ExclusiveStartKey"] = last_key


def collect_league_keys(canonical_league_id: str) -> list[dict]:
    """
    Collect the keys of every DynamoDB item belonging to a league.

    This covers two key spaces:
      * everything under the canonical PK (METADATA and all precomputed views,
        including any future SK types) read with strong consistency, and
      * the LEAGUE_LOOKUP items, which live under their own per-platform PKs and
        are located via GSI1 (eventually consistent).

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A list of {"PK", "SK"} key dicts for every item owned by the league.
    """
    keys = _query_all_keys(
        {
            "KeyConditionExpression": Key("PK").eq(f"LEAGUE#{canonical_league_id}"),
            "ProjectionExpression": "PK, SK",
            "ConsistentRead": True,
        }
    )
    keys += _query_all_keys(
        {
            "IndexName": "GSI1",
            "KeyConditionExpression": Key("canonical_league_id").eq(
                canonical_league_id
            ),
            "ProjectionExpression": "PK, SK",
        }
    )
    return keys


def delete_all_league_items(canonical_league_id: str, max_attempts: int = 4) -> None:
    """
    Delete every DynamoDB item for a league, retrying until none remain.

    Rather than deleting a hardcoded set of SK prefixes, this discovers the
    league's actual items on each pass and deletes them, then re-verifies. This
    catches orphaned items (e.g. PLATFORM_MIGRATION#) regardless of SK type and
    tolerates GSI1 eventual-consistency lag on LEAGUE_LOOKUP items.

    Args:
        canonical_league_id: The canonical league ID.
        max_attempts: Number of delete+verify passes before giving up.

    Raises:
        HTTPException: 500 if items still remain after max_attempts.
    """
    for attempt in range(1, max_attempts + 1):
        keys = collect_league_keys(canonical_league_id)
        if not keys:
            return
        logger.info(
            "Delete attempt %d/%d: removing %d items for %s",
            attempt,
            max_attempts,
            len(keys),
            canonical_league_id,
        )
        with main.table.batch_writer() as writer:
            for key in keys:
                writer.delete_item(Key=key)
        time.sleep(0.5 * attempt)  # let GSI1 catch up before re-verifying

    remaining = collect_league_keys(canonical_league_id)
    if remaining:
        remaining_sks = [key["SK"] for key in remaining]
        logger.error(
            "Orphaned items remain for %s after %d attempts: %s",
            canonical_league_id,
            max_attempts,
            remaining_sks,
        )
        publish_failure(
            f"Orphaned items remain for league {canonical_league_id} after "
            f"{max_attempts} delete attempts: {remaining_sks}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fully delete league data",
        )


def _iter_owner_other_league_metadata(
    clerk_user_id: str, exclude_canonical_league_id: str
) -> Iterator[dict]:
    """Yield every METADATA item owned by ``clerk_user_id`` except the excluded league's.

    Scans GSI3 (the sparse all-METADATA index) with pagination, filtered to the caller's owned
    leagues, and skips the league being deleted / opted out by PK. Shared by the per-platform
    "does the user still own another …" checks so the GSI3 query shape and pagination loop live
    in exactly one place.

    Args:
        clerk_user_id: The owner whose other leagues are enumerated.
        exclude_canonical_league_id: Canonical id of the league to skip.

    Yields:
        The full METADATA item for each of the user's other owned leagues.
    """
    excluded_pk = f"LEAGUE#{exclude_canonical_league_id}"
    kwargs: dict[str, Any] = {
        "IndexName": "GSI3",
        "KeyConditionExpression": Key("SK").eq("METADATA"),
        "FilterExpression": Attr("owner_user_id").eq(clerk_user_id),
    }
    while True:
        response = main.table.query(**kwargs)
        for item in response.get("Items", []):
            if item.get("PK") == excluded_pk:
                continue
            yield item
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return
        kwargs["ExclusiveStartKey"] = last_key


def owner_has_other_yahoo_leagues(
    clerk_user_id: str, exclude_canonical_league_id: str
) -> bool:
    """Return whether ``clerk_user_id`` owns a Yahoo league other than the excluded one.

    Used by ``delete_league`` to decide whether the owner's per-user ``YAHOO_OAUTH``
    token item is still needed: a single linked Yahoo account backs all of that
    user's Yahoo leagues, so the token must survive as long as any other Yahoo
    league remains (backend/delete-league, backend/yahoo-oauth).

    Queries GSI3 (the sparse all-METADATA index), filters to the caller's owned
    leagues, and inspects each one's effective platform (``active_platform`` falling
    back to ``platform``, so a league migrated *to* Yahoo counts and one migrated
    *away* from Yahoo does not). The league being deleted is skipped by PK.

    Args:
        clerk_user_id: The owner whose remaining Yahoo leagues are counted.
        exclude_canonical_league_id: Canonical id of the league being deleted.

    Returns:
        ``True`` if at least one *other* Yahoo league is owned by the user.
    """
    for item in _iter_owner_other_league_metadata(
        clerk_user_id, exclude_canonical_league_id
    ):
        effective_platform = item.get("active_platform") or item.get("platform")
        if effective_platform == main.Platform.YAHOO.value:
            return True
    return False


def owner_has_other_optedin_espn_leagues(
    clerk_user_id: str, exclude_canonical_league_id: str
) -> bool:
    """Return whether ``clerk_user_id`` owns another ESPN league opted into auto-refresh.

    Used to decide whether the owner's per-user ``ESPN_CREDENTIALS`` item is still needed: one
    stored ESPN session backs all of that user's ESPN leagues, so the cookies must survive as
    long as any *other* ESPN league they own is opted into automatic refresh
    (backend/espn-credential-storage, backend/delete-league).

    Queries GSI3 (the sparse all-METADATA index), filters to the caller's owned leagues, and
    inspects each one's effective platform (``active_platform`` falling back to ``platform``). GSI3
    does not project ``auto_refresh_enabled``, so for each *other* ESPN league it reads that item's
    METADATA to check the flag. The league being deleted / opted out is skipped by PK.

    Args:
        clerk_user_id: The owner whose remaining opted-in ESPN leagues are counted.
        exclude_canonical_league_id: Canonical id of the league being deleted / opted out.

    Returns:
        ``True`` if at least one *other* ESPN league owned by the user is opted into auto-refresh.
    """
    for item in _iter_owner_other_league_metadata(
        clerk_user_id, exclude_canonical_league_id
    ):
        effective_platform = item.get("active_platform") or item.get("platform")
        if effective_platform != main.Platform.ESPN.value:
            continue
        # auto_refresh_enabled is not projected into GSI3, so read the METADATA item.
        pk = item["PK"]
        full = main.table.get_item(Key={"PK": pk, "SK": "METADATA"}).get("Item", {})
        if full.get("auto_refresh_enabled"):
            return True
    return False


def create_job_status(
    correlation_id: str,
    request_type: str,
    league_id: str | None = None,
    platform: str | None = None,
    canonical_league_id: str | None = None,
) -> None:
    """
    Create the initial IN_PROGRESS JOB_STATUS item for a triggered job.

    Keyed by correlation_id so it is reachable by the frontend even when no
    league lookup record exists yet (e.g. a brand-new onboard). The onboarder /
    processor later upsert this same item to FAILED / COMPLETED. Best-effort: a
    failure here is logged but does not block triggering the job (the onboarder
    upserts the item regardless).

    Args:
        correlation_id: The job's correlation ID (its key).
        request_type: "ONBOARD" | "REFRESH" | "MIGRATE".
        league_id: The platform league ID (observability).
        platform: The platform, e.g. "ESPN" / "SLEEPER" (observability).
        canonical_league_id: The canonical league ID, when known (observability).
    """
    now = datetime.now(timezone.utc)
    item: dict[str, Any] = {
        "PK": f"JOB#{correlation_id}",
        "SK": "JOB_STATUS",
        "status": "IN_PROGRESS",
        "request_type": request_type,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "ttl": int(now.timestamp()) + JOB_TTL_SECONDS,
    }
    if league_id:
        item["league_id"] = league_id
    if platform:
        item["platform"] = platform
    if canonical_league_id:
        item["canonical_league_id"] = canonical_league_id
    try:
        main.table.put_item(Item=item)
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to create JOB_STATUS for %s: %s", correlation_id, e)


def get_job_status(correlation_id: str) -> dict | None:
    """
    Fetch a job's JOB_STATUS item, or None if it has expired / never existed.

    Args:
        correlation_id: The job's correlation ID.

    Returns:
        The JOB_STATUS item dict, or None.
    """
    try:
        response = main.table.get_item(
            Key={"PK": f"JOB#{correlation_id}", "SK": "JOB_STATUS"}
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status",
        )
    return response.get("Item")


def set_active_job(canonical_league_id: str, correlation_id: str) -> None:
    """
    Point a league's METADATA at its in-flight job (concurrency-guard pointer).

    Stores ``active_job_id`` on METADATA so a subsequent request can dereference
    the current job and reject duplicates while it is IN_PROGRESS. Best-effort.

    Args:
        canonical_league_id: The canonical league ID (must already have METADATA).
        correlation_id: The job's correlation ID to record as active.
    """
    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression="SET active_job_id = :j",
            ExpressionAttributeValues={":j": correlation_id},
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to set active_job_id for %s: %s", canonical_league_id, e)


def is_job_in_progress(metadata: dict) -> bool:
    """
    Whether a league has an in-flight onboard/refresh/migrate job.

    Dereferences the METADATA ``active_job_id`` pointer to the JOB_STATUS item;
    a missing/expired job or a terminal status means no job is in progress (the
    JOB_STATUS TTL also releases stuck jobs after 24h).

    Args:
        metadata: The league's METADATA item.

    Returns:
        True only if the referenced job exists and is IN_PROGRESS.
    """
    active_job_id = metadata.get("active_job_id")
    if not active_job_id:
        return False
    job = get_job_status(active_job_id)
    return bool(job) and job.get("status") == "IN_PROGRESS"


def require_league_owner(
    canonical_league_id: str, clerk_user_id: str, metadata: dict | None = None
) -> None:
    """
    Gate a mutating action to the league's owner (backend/league-authorization).

    The owner is the Clerk user who first onboarded the league
    (``owner_user_id`` on METADATA). Any other caller — or a league with no
    recorded owner — is rejected with ``403 Forbidden``.

    Args:
        canonical_league_id: The canonical league ID.
        clerk_user_id: The authenticated caller's Clerk user ID.
        metadata: Optional pre-fetched METADATA item; read from DynamoDB when omitted.
            Pass it to avoid a redundant read when the caller already loaded it.

    Raises:
        HTTPException: 403 when the caller is not the owner (or no owner is set).
    """
    if metadata is None:
        metadata = get_league_metadata(canonical_league_id)
    owner = metadata.get("owner_user_id")
    if owner and owner == clerk_user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not the league owner",
    )


def require_league_member(
    canonical_league_id: str,
    clerk_user_id: str,
    platform,
    metadata: dict | None = None,
) -> None:
    """
    Gate reads of an ESPN league to its members (backend/league-authorization).

    ESPN league data is confidential (viewing it upstream requires the caller's
    ``espn_s2``/``SWID`` cookies), so only members may read it. Membership is the
    ``members`` string set on METADATA, plus the owner. **Sleeper reads stay open**
    (Sleeper's API is public), so this is a no-op for Sleeper leagues.

    Args:
        canonical_league_id: The canonical league ID.
        clerk_user_id: The authenticated caller's Clerk user ID.
        platform: The league's ``Platform``; the gate only applies to ESPN.
        metadata: Optional pre-fetched METADATA item; read from DynamoDB when omitted.

    Raises:
        HTTPException: 403 when an ESPN caller is neither the owner nor a member.
    """
    if platform == main.Platform.SLEEPER:
        return
    if metadata is None:
        metadata = get_league_metadata(canonical_league_id)
    owner = metadata.get("owner_user_id")
    members = metadata.get("members") or set()
    if clerk_user_id == owner or clerk_user_id in members:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not a member of this league",
    )


def record_league_access(canonical_league_id: str, metadata: dict) -> None:
    """
    Record that a league was just opened, for stale-league detection (backend/league-access-tracking).

    Writes a ``last_accessed_at`` ISO-8601 (UTC) timestamp on the league's METADATA
    item, throttled to at most once per hour: ``get_league`` already loaded
    ``metadata``, so a still-fresh timestamp short-circuits the write and a fresh
    access costs zero extra DynamoDB ops. The write is conditional on the item still
    existing and is fully best-effort — any failure (a concurrent delete, or any other
    DynamoDB error) is logged and swallowed so tracking never breaks the league read.

    Args:
        canonical_league_id: The canonical league ID.
        metadata: The already-fetched METADATA item, used for the throttle check.
    """
    now = datetime.now(timezone.utc)
    last_accessed = metadata.get("last_accessed_at")
    if last_accessed:
        try:
            age_seconds = (now - datetime.fromisoformat(last_accessed)).total_seconds()
            if age_seconds < main.LEAGUE_ACCESS_THROTTLE_SECONDS:
                return
        except (ValueError, TypeError):
            # Unparseable/naive stored value — fall through and overwrite it.
            pass

    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression="SET last_accessed_at = :t",
            ExpressionAttributeValues={":t": now.isoformat()},
            ConditionExpression="attribute_exists(PK)",
        )
    except botocore.exceptions.ClientError as e:
        # Best-effort: a conditional-check failure (league deleted concurrently) or
        # any other DynamoDB error must not affect the league read.
        logger.warning(
            "Failed to record access for league %s: %s", canonical_league_id, e
        )


def add_league_member(canonical_league_id: str, clerk_user_id: str) -> None:
    """
    Add a verified caller to a league's ``members`` set (backend/league-authorization).

    Idempotent: ``ADD`` to a DynamoDB string set is a no-op when the value is
    already present. Used by the ESPN membership-verification flow once the
    caller's cookies are confirmed valid for the league.

    Args:
        canonical_league_id: The canonical league ID.
        clerk_user_id: The Clerk user ID to grant read membership.
    """
    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression="ADD members :m",
            ExpressionAttributeValues={":m": {clerk_user_id}},
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to add member to league %s: %s", canonical_league_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record league membership",
        )


def _is_conditional_check_failure(exc: botocore.exceptions.ClientError) -> bool:
    """True when a DynamoDB ClientError is a failed ConditionExpression."""
    return (
        exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"
    )
