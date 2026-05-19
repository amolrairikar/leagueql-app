import json
import os
import random

import boto3

from utils import build_retry_session, logger

s3_client = boto3.client("s3")
http_session = build_retry_session()
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
SLEEPER_NFL_STATE_URL = "https://api.sleeper.app/v1/state/nfl"
PLAYER_METADATA_S3_KEY = "player-metadata/sleeper_nfl_players.json"
REQUIRED_PLAYER_FIELDS = {"first_name", "last_name", "position"}


def fetch_nfl_state() -> dict | None:
    try:
        response = http_session.get(SLEEPER_NFL_STATE_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning("Failed to fetch NFL state: %s", e)
        return None


def lambda_handler(event, context) -> None:
    logger.info("Event data: %s", event)
    logger.info("Context data: %s", context)

    nfl_state = fetch_nfl_state()
    if nfl_state and nfl_state.get("season_type") == "off":
        logger.info("NFL season_type is 'off' — skipping player metadata fetch.")
        return

    bucket = os.environ["S3_BUCKET_NAME"]
    logger.info("Fetching Sleeper NFL player metadata from %s", SLEEPER_PLAYERS_URL)

    try:
        response = http_session.get(SLEEPER_PLAYERS_URL, timeout=60)
        response.raise_for_status()
        players_data = response.json()
        if not isinstance(players_data, dict) or not players_data:
            raise ValueError(
                f"Unexpected player metadata response: expected non-empty dict, got {type(players_data).__name__}"
            )
        sample_players = random.sample(
            list(players_data.values()), min(10, len(players_data))
        )
        missing_fields = REQUIRED_PLAYER_FIELDS - set.intersection(
            *(set(p.keys()) for p in sample_players)
        )
        if missing_fields:
            raise ValueError(
                f"Player metadata missing required fields: {missing_fields}"
            )
        logger.info("Fetched metadata for %d players", len(players_data))
    except Exception as e:
        logger.error("Failed to fetch player metadata: %s", e)
        raise

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
