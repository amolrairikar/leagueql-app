import os
from collections import defaultdict

import boto3
import requests

from common.logging_utils import logger  # noqa: F401  re-exported for handler import
from common.onboarder_invoke import invoke_onboarder

SLEEPER_BASE_URL = "https://api.sleeper.app/v1"

DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]
ONBOARDER_LAMBDA_NAME = os.environ["ONBOARDER_LAMBDA_NAME"]

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


def get_sleeper_leagues() -> list[dict]:
    """
    Queries DynamoDB for all Sleeper league IDs using GSI2.

    Returns:
        list[dict]: List of dicts with league_id and canonical_league_id for the most recent season of each Sleeper league.

    Raises:
        Exception: If DynamoDB query fails.
    """
    items = []
    kwargs: dict = {
        "TableName": DYNAMODB_TABLE_NAME,
        "IndexName": "GSI2",
        "KeyConditionExpression": "#p = :platform",
        "ExpressionAttributeNames": {"#p": "platform"},
        "ExpressionAttributeValues": {":platform": {"S": "SLEEPER"}},
    }

    while True:
        response = _dynamodb_client.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    # Group by canonical_league_id and select the most recent season
    leagues_by_canonical = defaultdict(list)
    for item in items:
        canonical_league_id = item.get("canonical_league_id", {}).get("S")
        league_id = item.get("league_id", {}).get("S")
        seasons = item.get("seasons", {}).get("SS", [])

        if canonical_league_id and league_id and seasons:
            # Get the most recent season from the seasons list
            most_recent_season = max(seasons, key=int)
            leagues_by_canonical[canonical_league_id].append(
                {"league_id": league_id, "season": most_recent_season}
            )

    # For each canonical league, select the league_id with the most recent season
    result = []
    for canonical_id, league_data in leagues_by_canonical.items():
        league_data.sort(key=lambda x: int(x["season"]), reverse=True)
        best = league_data[0]
        result.append(
            {"league_id": best["league_id"], "canonical_league_id": canonical_id}
        )

    return result


def invoke_onboarder_lambda(
    league_id: str, canonical_league_id: str, correlation_id: str
) -> None:
    """
    Invokes the onboarder lambda to refresh a specific Sleeper league asynchronously.

    Args:
        league_id: The Sleeper league ID to refresh.
        canonical_league_id: The canonical league ID, passed through to skip chain resolution.
        correlation_id: Correlation ID to propagate for request tracing.

    Raises:
        Exception: If lambda invocation fails.
    """
    response = invoke_onboarder(
        lambda_client=_lambda_client,
        function_name=ONBOARDER_LAMBDA_NAME,
        body={"leagueId": league_id, "platform": "SLEEPER"},
        request_type="REFRESH",
        canonical_league_id=canonical_league_id,
        correlation_id=correlation_id,
    )

    # Check if invocation was successful
    status_code = response.get("StatusCode")
    if status_code != 202:
        raise Exception(f"Lambda invocation failed with status code {status_code}")
