"""
delete_test_league.py

Deletes all DynamoDB items and S3 files for a given Sleeper or ESPN league.
Deletes directly from DynamoDB and S3 by canonical league ID, bypassing the
owner-gated delete API (this is an admin utility, not an authenticated caller).

Usage:
    pipenv run python scripts/utility_scripts/delete_test_league.py --league-id 1234567890 --platform sleeper
    pipenv run python scripts/utility_scripts/delete_test_league.py --league-id 1234567890 --platform espn

    # Target prod instead of dev (defaults to dev):
    pipenv run python scripts/utility_scripts/delete_test_league.py --league-id 1234567890 --platform sleeper --env prod

    # --league-id falls back to the TEST_SLEEPER_LEAGUE_ID environment variable:
    pipenv run python scripts/utility_scripts/delete_test_league.py --platform sleeper
"""

import argparse
import os
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(
        description="Delete all DynamoDB and S3 data for a Sleeper or ESPN league."
    )
    p.add_argument(
        "--league-id",
        default=os.environ.get("TEST_SLEEPER_LEAGUE_ID"),
        help="League ID (defaults to TEST_SLEEPER_LEAGUE_ID env var)",
    )
    p.add_argument(
        "--platform",
        required=True,
        choices=["sleeper", "espn"],
        help="League platform (sleeper or espn)",
    )
    p.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Target environment; selects the table and bucket (default: dev)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.league_id:
        print("Error: --league-id is required or set TEST_SLEEPER_LEAGUE_ID")
        sys.exit(1)

    account_id = os.environ.get("AWS_ACCOUNT_ID", "")
    if not account_id:
        print("Error: AWS_ACCOUNT_ID environment variable is required")
        sys.exit(1)

    # Set required env vars before importing main (module-level reads).
    os.environ["DYNAMODB_TABLE_NAME"] = f"leagueql-table-{args.env}"
    os.environ["S3_BUCKET_NAME"] = f"leagueql-{args.env}-bucket-east-{account_id}"

    _SRC = Path(__file__).parents[2] / "src"
    sys.path.insert(0, str(_SRC / "api"))
    sys.path.insert(0, str(_SRC))  # makes the shared ``common`` package importable

    import main
    from fastapi import HTTPException
    from main import (
        Platform,
        delete_all_league_items,
        lookup_league,
        update_league_count,
    )

    platform = Platform(args.platform)

    # Resolve the league's canonical ID first. lookup_league raises 404 when the
    # league isn't onboarded, in which case there is nothing to delete.
    try:
        canonical_league_id = lookup_league(league_id=args.league_id, platform=platform)
    except HTTPException as e:
        if e.status_code == 404:
            print(f"League {args.league_id} not found — nothing to delete")
            sys.exit(0)
        print(f"Error resolving league: {e.detail}")
        sys.exit(1)

    # Delete straight from DynamoDB and S3 — no owner-gated API path. Deletes every
    # DynamoDB item for the canonical league ID, then every S3 object under its
    # raw-api-data/ prefix, then decrements the public league counter.
    delete_all_league_items(canonical_league_id=canonical_league_id)

    s3_prefix = f"raw-api-data/{canonical_league_id}/"
    paginator = main.s3_client.get_paginator("list_objects_v2")
    deleted_objects = 0
    for page in paginator.paginate(Bucket=main.S3_BUCKET, Prefix=s3_prefix):
        delete_keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if not delete_keys:
            continue
        # S3 delete_objects handles up to 1,000 keys per request; each paginator
        # page is already capped at 1,000 keys, so one call per page is safe.
        main.s3_client.delete_objects(
            Bucket=main.S3_BUCKET,
            Delete={"Objects": delete_keys, "Quiet": True},
        )
        deleted_objects += len(delete_keys)

    update_league_count(delta=-1)

    print(
        f"Successfully deleted {platform.value} league {args.league_id} "
        f"(canonical {canonical_league_id}, {deleted_objects} S3 objects) from {args.env}"
    )
