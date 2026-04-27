import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import requests

from logging_utils import logger

s3_client = boto3.client("s3")
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
SLEEPER_NFL_STATE_URL = "https://api.sleeper.app/v1/state/nfl"
SLEEPER_STATS_URL = (
    "https://api.sleeper.com/stats/nfl/player/{player_id}"
    "?season_type=regular&season={season}"
)
PLAYER_METADATA_S3_KEY = "player-metadata/sleeper_nfl_players.json"
PLAYER_STATS_S3_KEY = "player-stats/sleeper_nfl_player_stats.json"

STATS_CONCURRENCY = 10


def fetch_nfl_state() -> dict | None:
    try:
        response = requests.get(SLEEPER_NFL_STATE_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning("Failed to fetch NFL state: %s", e)
        return None


def fetch_player_stats_for_season(
    player_id: str, season: str
) -> tuple[str, dict | None]:
    url = SLEEPER_STATS_URL.format(player_id=player_id, season=season)
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            return player_id, None
        response.raise_for_status()
        data = response.json()
        return player_id, data.get("stats") if data else None
    except Exception as e:
        logger.warning(
            "Failed to fetch stats for player %s season %s: %s", player_id, season, e
        )
        return player_id, None


def load_existing_player_stats(bucket: str) -> dict:
    try:
        response = s3_client.get_object(Bucket=bucket, Key=PLAYER_STATS_S3_KEY)
        return json.loads(response["Body"].read())
    except Exception as e:
        logger.warning("Could not load existing player stats from S3: %s", e)
        return {}


def update_player_stats(bucket: str, players_data: dict, season: str) -> None:
    active_player_ids = [
        pid for pid, meta in players_data.items() if meta.get("active")
    ]
    logger.info(
        "Fetching season %s stats for %d active players", season, len(active_player_ids)
    )

    stats = load_existing_player_stats(bucket)

    with ThreadPoolExecutor(max_workers=STATS_CONCURRENCY) as executor:
        futures = {
            executor.submit(fetch_player_stats_for_season, pid, season): pid
            for pid in active_player_ids
        }
        for future in as_completed(futures):
            player_id, result = future.result()
            if result is not None:
                if player_id not in stats:
                    stats[player_id] = {}
                stats[player_id][season] = result

    s3_client.put_object(
        Bucket=bucket,
        Key=PLAYER_STATS_S3_KEY,
        Body=json.dumps(stats),
        ContentType="application/json",
    )
    logger.info(
        "Successfully wrote player stats to s3://%s/%s", bucket, PLAYER_STATS_S3_KEY
    )


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

    nfl_state = fetch_nfl_state()
    if nfl_state and nfl_state.get("season_type") == "off":
        logger.info("NFL season_type is 'off' — skipping player metadata fetch.")
        return

    bucket = os.environ["S3_BUCKET_NAME"]
    logger.info("Fetching Sleeper NFL player metadata from %s", SLEEPER_PLAYERS_URL)

    try:
        response = requests.get(SLEEPER_PLAYERS_URL, timeout=60)
        response.raise_for_status()
        players_data = response.json()
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

    season = nfl_state.get("season") if nfl_state else None
    if season:
        update_player_stats(bucket, players_data, season)
    else:
        logger.warning("Could not determine current NFL season — skipping stats fetch.")
