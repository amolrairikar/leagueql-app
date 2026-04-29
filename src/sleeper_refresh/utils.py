import json
import os
from collections import defaultdict

import boto3
import requests

SLEEPER_BASE_URL = "https://api.sleeper.app/v1"


# TODO: Replace with proper logging
def logger() -> None:
    """Simple logger function for Lambda."""
    # In Lambda, this will use the default logger
    # For local testing, this is a no-op
    pass


def get_nfl_state() -> dict:
    """
    Fetches the current NFL state from Sleeper API.

    Returns:
        dict: NFL state response containing season_type and week.

    Raises:
        requests.exceptions.HTTPError: If the API request fails.
    """
    url = f"{SLEEPER_BASE_URL}/state/nfl"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_sleeper_leagues() -> list[str]:
    """
    Queries DynamoDB for all Sleeper league IDs using GSI2.

    Returns:
        list[str]: List of league IDs for the most recent season of each Sleeper league.

    Raises:
        Exception: If DynamoDB query fails.
    """
    dynamodb = boto3.client("dynamodb")
    table_name = os.environ["DYNAMODB_TABLE_NAME"]

    # Query GSI2 for all SLEEPER platform items
    response = dynamodb.query(
        TableName=table_name,
        IndexName="GSI2",
        KeyConditionExpression="platform = :platform",
        ExpressionAttributeValues={":platform": {"S": "SLEEPER"}},
    )

    items = response.get("Items", [])

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
        # Sort by season descending and take the first one
        league_data.sort(key=lambda x: int(x["season"]), reverse=True)
        result.append(league_data[0]["league_id"])

    return result


def invoke_onboarder_lambda(league_id: str) -> None:
    """
    Invokes the onboarder lambda to refresh a specific Sleeper league.

    Args:
        league_id: The Sleeper league ID to refresh.

    Raises:
        Exception: If lambda invocation fails.
    """
    lambda_client = boto3.client("lambda")
    onboarder_lambda_name = os.environ["ONBOARDER_LAMBDA_NAME"]

    payload = {
        "requestType": "REFRESH",
        "body": {"leagueId": league_id, "platform": "SLEEPER"},
    }

    response = lambda_client.invoke(
        FunctionName=onboarder_lambda_name,
        InvocationType="Event",  # Asynchronous invocation
        Payload=json.dumps(payload),
    )

    # Check if invocation was successful
    status_code = response.get("StatusCode")
    if status_code != 202:
        raise Exception(f"Lambda invocation failed with status code {status_code}")
