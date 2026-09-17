"""Yahoo player-data refresher (backend/yahoo-player-stats-refresher).

Scheduled ECS Fargate task that fetches Yahoo NFL player metadata (name, position) and
per-player season fantasy scoring, then caches them in S3 for the processing pipeline to read
(``player-metadata/yahoo_nfl_players.json`` and ``player-stats/yahoo_nfl_player_stats.json``).

Unlike the onboarder (which uses each user's linked token), this task uses a **dedicated service
credential** — the maintainer's own linked Yahoo account, addressed by ``YAHOO_SERVICE_USER_ID``
via the shared ``common.yahoo_tokens`` engine. Player fantasy points are read under the service
account's league (``YAHOO_SERVICE_LEAGUE_KEY``), whose season-specific scoring is applied by Yahoo.
"""

import json
import os
import time
from typing import Any

import boto3
import botocore.exceptions
from utils import build_retry_session, logger

from common.yahoo_tokens import from_env as yahoo_tokens_from_env

s3_client = boto3.client("s3")
http_session = build_retry_session()

YAHOO_BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"
PLAYER_METADATA_S3_KEY = "player-metadata/yahoo_nfl_players.json"
PLAYER_STATS_S3_KEY = "player-stats/yahoo_nfl_player_stats.json"
PAGE_SIZE = 25
# Pace paged requests to stay well within Yahoo's rate limits.
TARGET_INTERVAL = 0.25


# --------------------------------------------------------------------------------------
# Minimal Yahoo JSON normalization (kept local so this task deploys independently)
# --------------------------------------------------------------------------------------
def _flatten(node: Any) -> dict[str, Any]:
    if isinstance(node, dict):
        return node
    merged: dict[str, Any] = {}
    if isinstance(node, list):
        for element in node:
            if isinstance(element, dict):
                merged.update(element)
            elif isinstance(element, list):
                merged.update(_flatten(element))
    return merged


def _collection_items(container: Any, inner_key: str) -> list[Any]:
    if not isinstance(container, dict):
        return []
    items, index = [], 0
    while str(index) in container:
        entry = container[str(index)]
        index += 1
        if isinstance(entry, dict) and inner_key in entry:
            items.append(entry[inner_key])
    return items


def _league_subresource(payload: dict[str, Any], key: str) -> Any:
    league = payload.get("fantasy_content", {}).get("league", [])
    for element in league[1:] if isinstance(league, list) else []:
        if isinstance(element, dict) and key in element:
            return element[key]
    return None


def _get_json(url: str, access_token: str) -> dict[str, Any]:
    response = http_session.get(
        url, headers={"Authorization": f"Bearer {access_token}"}, timeout=30
    )
    response.raise_for_status()
    return response.json()


def _resolve_season(league_key: str, access_token: str) -> str:
    """Return the service league's season (used as the stats-cache season key)."""
    override = os.environ.get("SEASON")
    if override:
        return str(override)
    payload = _get_json(
        f"{YAHOO_BASE_URL}/league/{league_key};out=metadata?format=json", access_token
    )
    league = payload.get("fantasy_content", {}).get("league", [])
    meta = _flatten(league[0]) if isinstance(league, list) and league else {}
    season = meta.get("season")
    if not season:
        raise RuntimeError(f"Could not resolve season for league {league_key}")
    return str(season)


def _fetch_players_page(league_key: str, start: int, access_token: str) -> list[dict]:
    """Fetch one page of the league's players with season scoring; return flattened rows."""
    url = (
        f"{YAHOO_BASE_URL}/league/{league_key}/players;start={start};count={PAGE_SIZE}"
        "/stats?format=json"
    )
    payload = _get_json(url, access_token)
    players = _collection_items(_league_subresource(payload, "players") or {}, "player")
    rows = []
    for player in players:
        flat = _flatten(player)
        name = _flatten(flat.get("name", {}))
        points = _flatten(flat.get("player_points", {}))
        rows.append(
            {
                "player_key": flat.get("player_key"),
                "name": name.get("full"),
                "position": flat.get("display_position"),
                "total_points": points.get("total"),
            }
        )
    return rows


def _load_existing(bucket: str, key: str) -> dict:
    """Read an existing JSON cache from S3, bootstrapping empty when absent."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = json.loads(response["Body"].read())
        return data if isinstance(data, dict) else {}
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            logger.info("No existing cache at %s — starting fresh.", key)
            return {}
        raise


def main() -> None:
    bucket = os.environ["S3_BUCKET_NAME"]
    service_user_id = os.environ["YAHOO_SERVICE_USER_ID"]
    league_key = os.environ["YAHOO_SERVICE_LEAGUE_KEY"]
    # Test-only overrides: cap the fan-out and redirect the stats write so an integration run
    # exercises the full path without clobbering the production cache.
    max_players = os.environ.get("MAX_PLAYERS")
    stats_output_key = os.environ.get("OUTPUT_KEY") or PLAYER_STATS_S3_KEY

    token_client = yahoo_tokens_from_env()
    access_token = token_client.get_valid_access_token(service_user_id)
    season = _resolve_season(league_key, access_token)
    logger.info("Refreshing Yahoo player data for season %s", season)

    metadata = _load_existing(bucket, PLAYER_METADATA_S3_KEY)
    stats = _load_existing(bucket, stats_output_key)

    start, processed = 0, 0
    limit = int(max_players) if max_players else None
    while True:
        # Refresh the token periodically for long runs (proactive; refreshes near expiry).
        access_token = token_client.get_valid_access_token(service_user_id)
        page_start = time.monotonic()
        page = _fetch_players_page(league_key, start, access_token)
        if not page:
            break
        for row in page:
            key = row.get("player_key")
            if not key:
                continue
            metadata[key] = {"name": row.get("name"), "position": row.get("position")}
            if row.get("total_points") is not None:
                stats.setdefault(key, {})[season] = row["total_points"]
            processed += 1
            if limit and processed >= limit:
                break
        if limit and processed >= limit:
            logger.info("max_players override — stopping after %d players", processed)
            break
        start += PAGE_SIZE
        if processed % 200 == 0:
            logger.info("Processed %d players", processed)
        remaining = TARGET_INTERVAL - (time.monotonic() - page_start)
        if remaining > 0:
            time.sleep(remaining)

    s3_client.put_object(
        Bucket=bucket,
        Key=PLAYER_METADATA_S3_KEY,
        Body=json.dumps(metadata),
        ContentType="application/json",
    )
    s3_client.put_object(
        Bucket=bucket,
        Key=stats_output_key,
        Body=json.dumps(stats),
        ContentType="application/json",
    )
    logger.info(
        "Wrote Yahoo player data: %d players (metadata), %d players (stats) for season %s",
        len(metadata),
        len(stats),
        season,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
