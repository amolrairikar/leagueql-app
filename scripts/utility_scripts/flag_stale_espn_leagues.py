"""
flag_stale_espn_leagues.py

Scans every ESPN league in DynamoDB, determines how long since each was last
refreshed, and flags leagues that are stale beyond a threshold (default: 1 year).
Flagged leagues are deleted via the in-process ``delete_league`` API path (the same
code that powers DELETE /leagues/{id}), so DynamoDB and S3 cleanup happen
consistently.

Staleness is measured from ``last_refresh_at`` when present, otherwise from
``onboarded_at`` (a league onboarded long ago but never refreshed still counts).

The script is dry-run by default — it only reports what would be deleted. Pass
``--execute`` to actually delete the flagged leagues.

Usage:
    # Dry-run: report ESPN leagues that haven't refreshed in over a year
    pipenv run python scripts/utility_scripts/flag_stale_espn_leagues.py

    # Use a custom staleness window
    pipenv run python scripts/utility_scripts/flag_stale_espn_leagues.py --max-age-days 540

    # Actually delete the flagged leagues
    pipenv run python scripts/utility_scripts/flag_stale_espn_leagues.py --execute
"""

import argparse
import datetime
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

# Must set required env vars before importing main (module-level reads)
os.environ.setdefault("DYNAMODB_TABLE_NAME", "leagueql-table-dev")
account_id = os.environ.get("AWS_ACCOUNT_ID", "")
os.environ["S3_BUCKET_NAME"] = f"leagueql-dev-bucket-east-{account_id}"

_SRC = Path(__file__).parents[2] / "src"
sys.path.insert(0, str(_SRC / "api"))
sys.path.insert(0, str(_SRC))  # makes the shared ``common`` package importable

import boto3  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from helpers import get_league_metadata  # noqa: E402
from main import Platform, delete_league  # noqa: E402

DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_espn_leagues(region: str | None = None) -> list[dict]:
    """
    Queries DynamoDB via GSI2 for every ESPN league.

    Args:
        region: Optional AWS region for the DynamoDB client.

    Returns:
        A list of ``{"league_id": ..., "canonical_league_id": ...}`` dicts, one per
        canonical league, using the platform league_id of its most recent season.
    """
    client = (
        boto3.client("dynamodb", region_name=region)
        if region
        else boto3.client("dynamodb")
    )

    items: list[dict] = []
    kwargs: dict = {
        "TableName": DYNAMODB_TABLE_NAME,
        "IndexName": "GSI2",
        "KeyConditionExpression": "#p = :platform",
        "ExpressionAttributeNames": {"#p": "platform"},
        "ExpressionAttributeValues": {":platform": {"S": Platform.ESPN.value}},
    }
    while True:
        response = client.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    # Group by canonical_league_id and pick the league_id of the most recent season.
    leagues_by_canonical = defaultdict(list)
    for item in items:
        canonical_league_id = item.get("canonical_league_id", {}).get("S")
        league_id = item.get("league_id", {}).get("S")
        seasons = item.get("seasons", {}).get("SS", [])

        if canonical_league_id and league_id and seasons:
            most_recent_season = max(seasons, key=int)
            leagues_by_canonical[canonical_league_id].append(
                {"league_id": league_id, "season": most_recent_season}
            )

    result = []
    for canonical_id, league_data in leagues_by_canonical.items():
        league_data.sort(key=lambda x: int(x["season"]), reverse=True)
        best = league_data[0]
        result.append(
            {"league_id": best["league_id"], "canonical_league_id": canonical_id}
        )

    return result


def parse_timestamp(value: str) -> datetime.datetime:
    """Parses an ISO 8601 timestamp, tolerating a trailing ``Z`` for UTC."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=(
            "Flag (and optionally delete) ESPN leagues whose last refresh is older "
            "than a threshold. Dry-run unless --execute is passed."
        )
    )
    p.add_argument(
        "--max-age-days",
        type=int,
        default=365,
        help="Flag leagues last refreshed more than this many days ago (default: 365).",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Actually delete flagged leagues. Without this flag the script is dry-run.",
    )
    p.add_argument(
        "--region",
        default=None,
        help="AWS region (optional; defaults to the AWS config/environment).",
    )
    p.add_argument("--debug", action="store_true", help="Enable DEBUG logging.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if not account_id:
        logger.error("AWS_ACCOUNT_ID environment variable is required")
        sys.exit(1)

    now = datetime.datetime.now(datetime.timezone.utc)
    threshold = datetime.timedelta(days=args.max_age_days)

    leagues = get_espn_leagues(region=args.region)
    logger.info("Found %d ESPN league(s) to evaluate", len(leagues))

    flagged: list[dict] = []
    for league in leagues:
        league_id = league["league_id"]
        canonical_league_id = league["canonical_league_id"]
        try:
            metadata = get_league_metadata(canonical_league_id=canonical_league_id)
        except HTTPException as e:
            logger.warning(
                "Skipping league %s (canonical %s): could not read metadata (%s)",
                league_id,
                canonical_league_id,
                e.detail,
            )
            continue

        reference_ts = metadata.get("last_refresh_at") or metadata.get("onboarded_at")
        if not reference_ts:
            logger.warning(
                "Skipping league %s (canonical %s): no last_refresh_at or onboarded_at",
                league_id,
                canonical_league_id,
            )
            continue

        age = now - parse_timestamp(reference_ts)
        if age > threshold:
            logger.info(
                "FLAGGED league %s (canonical %s): last activity %s (%d days ago)",
                league_id,
                canonical_league_id,
                reference_ts,
                age.days,
            )
            flagged.append(league)
        else:
            logger.debug(
                "OK league %s (canonical %s): last activity %s (%d days ago)",
                league_id,
                canonical_league_id,
                reference_ts,
                age.days,
            )

    logger.info(
        "%d of %d ESPN league(s) are stale (> %d days)",
        len(flagged),
        len(leagues),
        args.max_age_days,
    )

    if not args.execute:
        if flagged:
            logger.info(
                "Dry-run: %d league(s) would be deleted. Re-run with --execute to delete.",
                len(flagged),
            )
        return

    deleted = 0
    failed = 0
    for league in flagged:
        league_id = league["league_id"]
        try:
            delete_league(leagueId=league_id, platform=Platform.ESPN)
            logger.info("Deleted league %s", league_id)
            deleted += 1
        except HTTPException as e:
            if e.status_code == 404:
                logger.info("League %s not found — nothing to delete", league_id)
                deleted += 1
            else:
                logger.error("Failed to delete league %s: %s", league_id, e.detail)
                failed += 1

    logger.info("Done: %d deleted, %d failed", deleted, failed)


if __name__ == "__main__":
    main()
