import os
import random
import time
from collections import defaultdict

import boto3
import requests

from common.logging_utils import logger
from common.onboarder_invoke import invoke_onboarder

SLEEPER_BASE_URL = "https://api.sleeper.app/v1"

DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]
ONBOARDER_LAMBDA_NAME = os.environ["ONBOARDER_LAMBDA_NAME"]

# Platforms auto-refreshed on a schedule. ESPN is excluded (it needs user-supplied
# cookies). Sleeper is public (no owner); Yahoo needs the owner's OAuth token, which
# the onboarder obtains from the owner_user_id passed in the invoke.
SLEEPER = "SLEEPER"
YAHOO = "YAHOO"
REFRESH_PLATFORMS = (SLEEPER, YAHOO)

# Pacing between consecutive onboarder dispatches to the same platform. Because the
# dispatch is an async ("Event") invoke, sleeping here staggers when each onboarder
# actually hits the platform API, so a run of many leagues does not burst it
# (backend/scheduled-league-auto-refresh). Both are env-tunable so pacing can be
# retuned without a redeploy.
DISPATCH_INTERVAL_SECONDS = float(
    os.environ.get("REFRESH_DISPATCH_INTERVAL_SECONDS", "3")
)
DISPATCH_JITTER_SECONDS = float(os.environ.get("REFRESH_DISPATCH_JITTER_SECONDS", "5"))

_dynamodb_client = boto3.client("dynamodb")
_lambda_client = boto3.client("lambda")


def get_nfl_state() -> dict:
    """
    Fetches the current NFL state from Sleeper API.

    Returns:
        dict: NFL state response containing season_type and week.

    Raises:
        requests.exceptions.HTTPError: If the API request fails.
    """
    url = f"{SLEEPER_BASE_URL}/state/nfl"
    response = requests.get(url, timeout=(5, 10))
    response.raise_for_status()
    return response.json()


def dispatch_sleep_seconds() -> float:
    """
    Returns the wait (base interval + random jitter) between consecutive
    same-platform dispatches. See ``DISPATCH_INTERVAL_SECONDS`` /
    ``DISPATCH_JITTER_SECONDS``.
    """
    # Jitter is load-spreading, not cryptographic, so the stdlib RNG is fine.
    return DISPATCH_INTERVAL_SECONDS + random.uniform(0, DISPATCH_JITTER_SECONDS)  # noqa: S311


def pace_dispatch() -> None:
    """Sleep between consecutive same-platform dispatches (see ``dispatch_sleep_seconds``)."""
    time.sleep(dispatch_sleep_seconds())


def _query_platform_lookups(platform: str) -> list[dict]:
    """Query GSI2 for every LEAGUE_LOOKUP item of ``platform`` (paginated)."""
    items: list[dict] = []
    kwargs: dict = {
        "TableName": DYNAMODB_TABLE_NAME,
        "IndexName": "GSI2",
        "KeyConditionExpression": "#p = :platform",
        "ExpressionAttributeNames": {"#p": "platform"},
        "ExpressionAttributeValues": {":platform": {"S": platform}},
    }
    while True:
        response = _dynamodb_client.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


def _most_recent_leagues(items: list[dict], current_season: int) -> list[dict]:
    """
    Group LEAGUE_LOOKUP ``items`` by canonical league and return the most-recent
    season's ``league_id`` per canonical, skipping any whose newest onboarded season
    is behind ``current_season`` (a completed prior season that cannot change).
    """
    leagues_by_canonical = defaultdict(list)
    for item in items:
        canonical_league_id = item.get("canonical_league_id", {}).get("S")
        league_id = item.get("league_id", {}).get("S")
        seasons = item.get("seasons", {}).get("SS", [])
        if canonical_league_id and league_id and seasons:
            most_recent_season = max(seasons, key=int)
            leagues_by_canonical[canonical_league_id].append(
                {"league_id": league_id, "season": most_recent_season}
            )

    result = []
    for canonical_id, league_data in leagues_by_canonical.items():
        league_data.sort(key=lambda x: int(x["season"]), reverse=True)
        best = league_data[0]
        # Skip leagues not yet onboarded for the current NFL season: their newest
        # onboarded season is a completed prior season whose data cannot change
        # (backend/scheduled-league-auto-refresh).
        if int(best["season"]) < current_season:
            continue
        result.append(
            {"league_id": best["league_id"], "canonical_league_id": canonical_id}
        )
    return result


def _pending_sleeper_renewals(items: list[dict], current_season: int) -> list[dict]:
    """
    Sleeper-only: a renewed season is registered as a LEAGUE_LOOKUP with a
    ``pending_season`` marker and no ``seasons`` before its season starts
    (backend/league-onboarding). Poll each so the season attaches automatically once
    it flips to in_season. Abandoned pending renewals (behind the current NFL season)
    are skipped.
    """
    result = []
    for item in items:
        canonical_league_id = item.get("canonical_league_id", {}).get("S")
        league_id = item.get("league_id", {}).get("S")
        seasons = item.get("seasons", {}).get("SS", [])
        pending_season = item.get("pending_season", {}).get("S")
        if canonical_league_id and league_id and pending_season and not seasons:
            if int(pending_season) < current_season:
                continue
            result.append(
                {"league_id": league_id, "canonical_league_id": canonical_league_id}
            )
    return result


def _get_league_owner(canonical_league_id: str) -> str | None:
    """
    Read ``owner_user_id`` from a canonical league's METADATA item. Yahoo refreshes
    need the owner's Clerk id so the onboarder can obtain/refresh that owner's OAuth
    token; the field lives only on METADATA (not on the LEAGUE_LOOKUP items GSI2
    returns). Returns None when the item or field is absent.
    """
    response = _dynamodb_client.get_item(
        TableName=DYNAMODB_TABLE_NAME,
        Key={
            "PK": {"S": f"LEAGUE#{canonical_league_id}"},
            "SK": {"S": "METADATA"},
        },
        ProjectionExpression="owner_user_id",
    )
    return response.get("Item", {}).get("owner_user_id", {}).get("S")


def get_leagues_to_refresh(current_season: int) -> list[dict]:
    """
    Enumerates the Sleeper and Yahoo leagues to refresh for the current NFL season.

    For each platform, queries DynamoDB GSI2, de-duplicates to the most recent
    onboarded season per canonical league, and skips leagues whose newest season is
    behind ``current_season``. Sleeper additionally polls pending renewals. Yahoo
    leagues resolve their ``owner_user_id`` from METADATA and are skipped when it is
    absent (they cannot be refreshed without an owner).

    Args:
        current_season: The current NFL season (year). Leagues and pending renewals
            whose season is strictly less than this are skipped.

    Returns:
        list[dict]: dicts with ``platform``, ``league_id``, ``canonical_league_id``,
            and ``owner_user_id`` (None for Sleeper).

    Raises:
        Exception: If a DynamoDB query fails.
    """
    result: list[dict] = []

    for platform in REFRESH_PLATFORMS:
        items = _query_platform_lookups(platform)
        leagues = _most_recent_leagues(items, current_season)

        if platform == SLEEPER:
            # Pending renewals are additional to a canonical's most-recent real season,
            # so a league mid-renewal is refreshed on both its current and pending ID.
            leagues.extend(_pending_sleeper_renewals(items, current_season))
            for league in leagues:
                result.append(
                    {
                        "platform": SLEEPER,
                        "league_id": league["league_id"],
                        "canonical_league_id": league["canonical_league_id"],
                        "owner_user_id": None,
                    }
                )
        else:  # YAHOO
            for league in leagues:
                owner_user_id = _get_league_owner(league["canonical_league_id"])
                if not owner_user_id:
                    logger.info(
                        "Skipping Yahoo league %s: no owner_user_id on METADATA",
                        league["league_id"],
                    )
                    continue
                result.append(
                    {
                        "platform": YAHOO,
                        "league_id": league["league_id"],
                        "canonical_league_id": league["canonical_league_id"],
                        "owner_user_id": owner_user_id,
                    }
                )

    return result


def invoke_onboarder_lambda(
    league_id: str,
    canonical_league_id: str,
    correlation_id: str,
    platform: str,
    owner_user_id: str | None = None,
) -> None:
    """
    Invokes the onboarder lambda to refresh a specific league asynchronously.

    Args:
        league_id: The platform league ID to refresh.
        canonical_league_id: The canonical league ID, passed through to skip chain resolution.
        correlation_id: Correlation ID to propagate for request tracing.
        platform: The platform (``SLEEPER`` or ``YAHOO``).
        owner_user_id: Clerk user ID of the league owner, required for Yahoo so the
            onboarder can obtain/refresh the owner's OAuth token; None for Sleeper.

    Raises:
        Exception: If lambda invocation fails.
    """
    response = invoke_onboarder(
        lambda_client=_lambda_client,
        function_name=ONBOARDER_LAMBDA_NAME,
        body={"leagueId": league_id, "platform": platform},
        request_type="REFRESH",
        canonical_league_id=canonical_league_id,
        correlation_id=correlation_id,
        owner_user_id=owner_user_id,
    )

    # Check if invocation was successful
    status_code = response.get("StatusCode")
    if status_code != 202:
        raise RuntimeError(f"Lambda invocation failed with status code {status_code}")
