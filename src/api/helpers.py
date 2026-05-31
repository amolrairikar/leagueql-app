"""Helper functions for the LeagueQL API.

DynamoDB access, Sleeper NFL state, SNS alerting, and small data utilities.
Functions that touch the patched singletons (``table``, ``_sns_client``) reach
them through the ``main`` module at call time so tests can patch ``main.table``
etc. and have it take effect here.
"""

import time
from decimal import Decimal
from typing import Any

import botocore.exceptions
import requests as http_requests
from boto3.dynamodb.conditions import Key
from fastapi import HTTPException, status

import main
from main import (
    SLEEPER_STATE_URL,
    SubscriptionStatus,
    correlation_id_var,
    logger,
)


def convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def publish_failure(error_message: str) -> None:
    if not main._sns_client:
        return
    try:
        main._sns_client.publish(
            TopicArn=main._sns_topic_arn,
            Subject="LeagueQL API Failure",
            Message=f"Correlation ID: {correlation_id_var.get()}\nError: {error_message}",
        )
    except Exception:
        logger.warning("Failed to publish SNS failure notification", exc_info=True)


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
    except Exception:
        logger.warning(
            "Failed to fetch NFL state; skipping refresh guard", exc_info=True
        )
        return None


def get_latest_stored_matchup(canonical_league_id: str) -> tuple[int, int] | None:
    """
    Finds the most recent stored matchup for a league.

    Matchups are keyed SK=MATCHUPS#{season}#WEEK#{week:02d}. Because season is
    4-digit and week is zero-padded, the lexicographically-largest MATCHUPS# SK
    is the latest stored season/week.

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A (season, week) tuple for the most recent stored matchup, or None if
        the league has no matchups stored.
    """
    try:
        response = main.table.query(
            KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical_league_id}")
            & Key("SK").begins_with("MATCHUPS#"),
            ScanIndexForward=False,
            Limit=1,
            ProjectionExpression="SK",
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )

    items = response.get("Items", [])
    if not items:
        return None
    # SK format: MATCHUPS#{season}#WEEK#{week}
    _, season, _, week = items[0]["SK"].split("#")
    return int(season), int(week)


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


def update_league_count(delta: int) -> None:
    main.table.update_item(
        Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
        UpdateExpression="ADD league_count :delta",
        ExpressionAttributeValues={":delta": Decimal(str(delta))},
    )


def update_subscription_status(
    canonical_league_id: str, new_status: SubscriptionStatus
) -> None:
    """
    Sets the subscription state on a league's METADATA item.

    Args:
        canonical_league_id: The canonical league ID.
        new_status: The subscription state to set.
    """
    # TODO(billing): no public/authenticated route exposes this yet. For now
    # subscription state is changed manually (script/console). A guarded endpoint
    # or payment-provider webhook backed by this helper is the enforcement-phase
    # follow-up.
    main.table.update_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
        UpdateExpression="SET subscription_status = :s",
        ConditionExpression="attribute_exists(PK)",
        ExpressionAttributeValues={":s": new_status.value},
    )
