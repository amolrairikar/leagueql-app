import json
import os

import boto3
import requests

from logging_utils import logger

s3_client = boto3.client("s3")
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
PLAYER_METADATA_S3_KEY = "player-metadata/sleeper_nfl_players.json"


def lambda_handler(event, context) -> None:
    """
    Fetch the Sleeper NFL player metadata file and cache it in S3.

    Invoked on a schedule by EventBridge every 2 days. Downloads the full
    player ID → metadata mapping from the Sleeper API and overwrites the
    cached copy at player-metadata/sleeper_nfl_players.json in the regional
    S3 bucket. The processor Lambda reads this file to enrich Sleeper matchup
    player stats with full names and positions.

    Args:
        event: The EventBridge scheduled event that triggered this invocation.
        context: The Lambda execution context.
    """
    logger.info("Event data: %s", event)
    logger.info("Context data: %s", context)

    bucket = os.environ["S3_BUCKET_NAME"]
    logger.info("Fetching Sleeper NFL player metadata from %s", SLEEPER_PLAYERS_URL)

    response = requests.get(SLEEPER_PLAYERS_URL, timeout=60)
    response.raise_for_status()
    players_data = response.json()
    logger.info("Fetched metadata for %d players", len(players_data))

    s3_client.put_object(
        Bucket=bucket,
        Key=PLAYER_METADATA_S3_KEY,
        Body=json.dumps(players_data),
        ContentType="application/json",
    )
    logger.info(
        "Successfully wrote player metadata to s3://%s/%s",
        bucket,
        PLAYER_METADATA_S3_KEY,
    )
