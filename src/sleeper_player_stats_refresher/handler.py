# Handler for sleeper player stats refresher lambda.
import json
import os
import time

import boto3
import botocore.exceptions
from utils import build_retry_session, logger

s3_client = boto3.client("s3")
http_session = build_retry_session()

SLEEPER_NFL_STATE_URL = "https://api.sleeper.app/v1/state/nfl"
SLEEPER_STATS_URL = "https://api.sleeper.com/stats/nfl/player/{player_id}?season_type=regular&season={season}"
PLAYER_METADATA_S3_KEY = "player-metadata/sleeper_nfl_players.json"
PLAYER_STATS_S3_KEY = "player-stats/sleeper_nfl_player_stats.json"
TARGET_INTERVAL = 60 / 925  # ~0.0649s between requests to stay under 925 req/min


def fetch_nfl_state() -> dict | None:
    try:
        response = http_session.get(SLEEPER_NFL_STATE_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:  # noqa: BLE001 — best-effort fetch; caller handles None
        logger.warning("Failed to fetch NFL state: %s", e)
        return None


def fetch_stats(player_id: str, season: str) -> dict | None:
    url = SLEEPER_STATS_URL.format(player_id=player_id, season=season)
    t_start = time.monotonic()
    try:
        response = http_session.get(url, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return data.get("stats") if isinstance(data, dict) else None
    finally:
        remaining = TARGET_INTERVAL - (time.monotonic() - t_start)
        if remaining > 0:
            time.sleep(remaining)


def main() -> None:
    bucket = os.environ["S3_BUCKET_NAME"]

    # An explicit ``SEASON`` env var (used for on-demand / integration-test runs)
    # forces a refresh for that season and bypasses the live NFL-state gating. The
    # scheduled task sets no ``SEASON``, so it keeps the original behavior: skip
    # during the off-season.
    season_override = os.environ.get("SEASON")
    # ``MAX_PLAYERS`` caps the fan-out and ``OUTPUT_KEY`` redirects the write — both
    # are test-only overrides so an integration run can validate the end-to-end path
    # against a small subset without clobbering the production stats cache. The
    # scheduled task supplies neither, keeping full production behavior.
    max_players = os.environ.get("MAX_PLAYERS")
    output_key = os.environ.get("OUTPUT_KEY") or PLAYER_STATS_S3_KEY
    if season_override:
        season = str(season_override)
        logger.info(
            "Season override '%s' supplied in event — bypassing NFL state check.",
            season,
        )
    else:
        nfl_state = fetch_nfl_state()
        if not nfl_state:
            logger.error("Could not fetch NFL state — aborting.")
            raise RuntimeError("Failed to fetch NFL state")
        if nfl_state.get("season_type") == "off":
            logger.info("NFL season is off — skipping player stats refresh.")
            return
        season = str(nfl_state["season"])
    response = s3_client.get_object(Bucket=bucket, Key=PLAYER_METADATA_S3_KEY)
    players = json.loads(response["Body"].read())

    # Team defenses (D/ST) carry no "status" field in Sleeper's player metadata —
    # they use an "active" boolean instead — so the status check alone drops every
    # defense and their draft picks end up with null scoring. Always fetch defenses
    # so the pipeline can compute their total_points / position ranks.
    active_ids = [
        pid
        for pid, meta in players.items()
        if meta.get("status") == "Active" or meta.get("position") == "DEF"
    ]
    if max_players:
        active_ids = active_ids[: int(max_players)]
        logger.info(
            "max_players override — limiting run to first %d active players",
            len(active_ids),
        )
    logger.info("Processing %d active players for season %s", len(active_ids), season)

    # A run only fetches the selected players for a single ``season``. Read the existing
    # cache and deep-merge into it so previously cached seasons for the same player and
    # players outside this run's selection are preserved (rather than overwriting the
    # object with just this season's slice). A missing object bootstraps an empty cache.
    try:
        existing_response = s3_client.get_object(Bucket=bucket, Key=output_key)
        all_stats = json.loads(existing_response["Body"].read())
        if not isinstance(all_stats, dict):
            all_stats = {}
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            logger.info("No existing stats cache at %s — starting fresh.", output_key)
            all_stats = {}
        else:
            raise

    total = len(active_ids)
    for index, player_id in enumerate(active_ids, start=1):
        stats = fetch_stats(player_id, season)
        if stats is not None:
            all_stats.setdefault(player_id, {})[season] = stats
        if index % 500 == 0:
            logger.info("Processed %d/%d players", index, total)

    s3_client.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=json.dumps(all_stats),
        ContentType="application/json",
    )
    logger.info(
        "Wrote stats for %d players to s3://%s/%s",
        len(all_stats),
        bucket,
        output_key,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
