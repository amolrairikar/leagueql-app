"""
fetch_player_stats.py

One-time backfill script that fetches per-season regular-season stats for every
player in the Sleeper player-metadata file and writes the result to S3.

Output shape (written to player-stats/sleeper_nfl_player_stats.json):
    {
        "<player_id>": {
            "2017": { ...stats dict or null... },
            "2018": { ...stats dict or null... },
            ...
        },
        ...
    }

Rate limiting: a semaphore caps concurrent requests so throughput stays at
~750 req/min (well under Sleeper's 1000 req/min hard limit). Each semaphore
slot is held for at least MIN_SLOT_TIME seconds, giving:
    max_throughput = CONCURRENCY / MIN_SLOT_TIME req/s

Usage:
    # Activate the pipenv shell first (run once per session)
    pipenv shell

    # Fetch all player stats (2017 - current season) and write to S3
    pipenv run python deployment_scripts/fetch_player_stats.py --bucket my-bucket

    # Resume from a previous run's local checkpoint
    pipenv run python deployment_scripts/fetch_player_stats.py --bucket my-bucket --checkpoint player_stats_checkpoint.json
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path

import aiohttp
import boto3
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

SLEEPER_STATS_URL = (
    "https://api.sleeper.com/stats/nfl/player/{player_id}"
    "?season_type=regular&season={season}"
)
PLAYER_METADATA_S3_KEY = "player-metadata/sleeper_nfl_players.json"
PLAYER_STATS_S3_KEY = "player-stats/sleeper_nfl_player_stats.json"

FIRST_SEASON = 2017
TARGET_RPS = 750 / 60  # ~12.5 requests/second
CONCURRENCY = 10  # concurrent in-flight requests
# Each semaphore slot is held for at least this long → max CONCURRENCY/MIN_SLOT_TIME req/s
MIN_SLOT_TIME = CONCURRENCY / TARGET_RPS  # ~0.8 s

CHECKPOINT_EVERY = 200  # checkpoint after every N fully-completed players
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # seconds; doubles on each retry

CURRENT_NFL_SEASON = 2025


def fetch_player_metadata(s3_client, bucket: str) -> dict:
    logger.info(
        "Fetching player metadata from s3://%s/%s", bucket, PLAYER_METADATA_S3_KEY
    )
    response = s3_client.get_object(Bucket=bucket, Key=PLAYER_METADATA_S3_KEY)
    return json.loads(response["Body"].read())


async def fetch_player_stats(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    player_id: str,
    season: int,
) -> tuple[str, int, dict | None]:
    url = SLEEPER_STATS_URL.format(player_id=player_id, season=season)
    result = None

    async with semaphore:
        t_start = asyncio.get_event_loop().time()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.get(url) as resp:
                    if resp.status == 404:
                        result = None
                        break
                    if resp.status == 429:
                        wait = RETRY_BACKOFF_BASE**attempt
                        logger.warning(
                            "Rate limited (429) on player %s season %d — waiting %.1fs",
                            player_id,
                            season,
                            wait,
                        )
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    data = await resp.json()
                    result = data.get("stats") if data else None
                    break
            except aiohttp.ClientError as exc:
                if attempt == MAX_RETRIES:
                    logger.warning(
                        "Giving up on player %s season %d after %d attempts: %s",
                        player_id,
                        season,
                        MAX_RETRIES,
                        exc,
                    )
                    break
                backoff = RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    "Request error for player %s season %d (attempt %d/%d): %s — retrying in %.1fs",
                    player_id,
                    season,
                    attempt,
                    MAX_RETRIES,
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)

        # Hold the semaphore slot for the remainder of MIN_SLOT_TIME so throughput
        # never exceeds CONCURRENCY / MIN_SLOT_TIME requests/second.
        elapsed = asyncio.get_event_loop().time() - t_start
        remaining = MIN_SLOT_TIME - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)

    return player_id, season, result


def save_checkpoint(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data))


def load_checkpoint(path: Path) -> dict:
    if path.exists():
        logger.info("Resuming from checkpoint at %s", path)
        return json.loads(path.read_text())
    return {}


def upload_to_s3(s3_client, bucket: str, data: dict) -> None:
    logger.info("Uploading player stats to s3://%s/%s", bucket, PLAYER_STATS_S3_KEY)
    s3_client.put_object(
        Bucket=bucket,
        Key=PLAYER_STATS_S3_KEY,
        Body=json.dumps(data),
        ContentType="application/json",
    )
    logger.info("Upload complete.")


async def run(args) -> None:
    seasons = list(range(args.start_season, CURRENT_NFL_SEASON + 1))
    checkpoint_path = Path(args.checkpoint)

    aws_session = boto3.Session(region_name=args.region)
    s3 = aws_session.client("s3")

    players = fetch_player_metadata(s3, args.bucket)
    player_ids = list(players.keys())
    logger.info(
        "Found %d player IDs; fetching seasons %d-%d",
        len(player_ids),
        seasons[0],
        seasons[-1],
    )

    stats: dict = load_checkpoint(checkpoint_path)
    remaining = [pid for pid in player_ids if pid not in stats]
    logger.info(
        "%d / %d players remaining (checkpoint has %d)",
        len(remaining),
        len(player_ids),
        len(stats),
    )

    if not remaining:
        logger.info("All players already in checkpoint — uploading directly.")
        upload_to_s3(s3, args.bucket, stats)
        return

    semaphore = asyncio.Semaphore(CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=30)

    # Accumulate in-progress results keyed by player_id; a set tracks pending seasons.
    pending_seasons: dict[str, set] = {pid: set(seasons) for pid in remaining}
    in_progress: dict[str, dict] = {pid: {} for pid in remaining}
    completed_players = 0

    total_calls = len(remaining) * len(seasons)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [
            asyncio.create_task(fetch_player_stats(session, semaphore, pid, season))
            for pid in remaining
            for season in seasons
        ]

        with tqdm(total=total_calls, desc="Fetching player stats", unit="req") as pbar:
            for coro in asyncio.as_completed(tasks):
                player_id, season, result = await coro
                if result is not None:
                    in_progress[player_id][str(season)] = result
                pending_seasons[player_id].discard(season)
                pbar.update(1)

                if not pending_seasons[player_id]:
                    stats[player_id] = in_progress.pop(player_id)
                    completed_players += 1

                    if completed_players % CHECKPOINT_EVERY == 0:
                        save_checkpoint(stats, checkpoint_path)
                        logger.info(
                            "Checkpoint saved — %d / %d players complete",
                            completed_players,
                            len(remaining),
                        )

    save_checkpoint(stats, checkpoint_path)
    upload_to_s3(s3, args.bucket, stats)
    logger.info("Done. Stats for %d players written to S3.", len(stats))


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Backfill Sleeper player stats (2017-present) into S3."
    )
    p.add_argument("--bucket", required=True, help="Target S3 bucket name")
    p.add_argument("--region", default=None, help="AWS region (optional)")
    p.add_argument(
        "--checkpoint",
        default="player_stats_checkpoint.json",
        help="Local checkpoint file for resumability (default: player_stats_checkpoint.json)",
    )
    p.add_argument(
        "--start-season",
        type=int,
        default=FIRST_SEASON,
        help=f"Earliest season to fetch (default: {FIRST_SEASON})",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
