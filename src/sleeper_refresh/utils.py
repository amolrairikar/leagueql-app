import json
import logging
import os
import time
from collections import defaultdict
from contextvars import ContextVar

import boto3
import requests

SLEEPER_BASE_URL = "https://api.sleeper.app/v1"

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class JsonFormatter(logging.Formatter):
    """Class to format logs in JSON format."""

    def format(self, record) -> str:
        log_object = {
            "timestamp": int(time.time() * 1000),
            "level": record.levelname,
            "message": record.getMessage(),
            "function": record.funcName,
            "correlation_id": correlation_id_var.get(),
        }
        return json.dumps(log_object)


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("leagueql")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    if not logger.handlers:
        logger.addHandler(handler)
    return logger


logger = setup_logger()

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


def get_sleeper_leagues() -> list[str]:
    """
    Queries DynamoDB for all Sleeper league IDs using GSI2.

    Returns:
        list[str]: List of league IDs for the most recent season of each Sleeper league.

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
        # Sort by season descending and take the first one
        league_data.sort(key=lambda x: int(x["season"]), reverse=True)
        result.append(league_data[0]["league_id"])

    return result


def invoke_onboarder_lambda(league_id: str, correlation_id: str) -> None:
    """
    Invokes the onboarder lambda to refresh a specific Sleeper league asynchronously.

    Args:
        league_id: The Sleeper league ID to refresh.
        correlation_id: Correlation ID to propagate for request tracing.

    Raises:
        Exception: If lambda invocation fails.
    """
    payload = {
        "requestType": "REFRESH",
        "body": {"leagueId": league_id, "platform": "SLEEPER"},
        "correlation_id": correlation_id,
    }

    response = _lambda_client.invoke(
        FunctionName=ONBOARDER_LAMBDA_NAME,
        InvocationType="Event",  # Asynchronous invocation
        Payload=json.dumps(payload),
    )

    # Check if invocation was successful
    status_code = response.get("StatusCode")
    if status_code != 202:
        raise Exception(f"Lambda invocation failed with status code {status_code}")
