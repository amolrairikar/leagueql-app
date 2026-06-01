"""
delete_test_league.py

Deletes all DynamoDB items and S3 files for a given Sleeper test league.
Reuses delete_league from the API to avoid duplicating deletion logic.

Usage:
    pipenv run python scripts/utility_scripts/delete_test_league.py --league-id 1234567890

    # Or fall back to the TEST_SLEEPER_LEAGUE_ID environment variable:
    pipenv run python scripts/utility_scripts/delete_test_league.py
"""

import argparse
import os
import sys
from pathlib import Path

# Must set required env vars before importing main (module-level reads)
os.environ.setdefault("DYNAMODB_TABLE_NAME", "leagueql-table-dev")
account_id = os.environ.get("AWS_ACCOUNT_ID", "")
os.environ["S3_BUCKET_NAME"] = f"leagueql-dev-bucket-east-{account_id}"

_SRC = Path(__file__).parents[2] / "src"
sys.path.insert(0, str(_SRC / "api"))
sys.path.insert(0, str(_SRC))  # makes the shared ``common`` package importable

from fastapi import HTTPException  # noqa: E402
from main import Platform, delete_league  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(
        description="Delete all DynamoDB and S3 data for a Sleeper test league."
    )
    p.add_argument(
        "--league-id",
        default=os.environ.get("TEST_SLEEPER_LEAGUE_ID"),
        help="Sleeper league ID (defaults to TEST_SLEEPER_LEAGUE_ID env var)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.league_id:
        print("Error: --league-id is required or set TEST_SLEEPER_LEAGUE_ID")
        sys.exit(1)
    if not account_id:
        print("Error: AWS_ACCOUNT_ID environment variable is required")
        sys.exit(1)

    try:
        delete_league(leagueId=args.league_id, platform=Platform.SLEEPER)
        print(f"Successfully deleted Sleeper league {args.league_id}")
    except HTTPException as e:
        if e.status_code == 404:
            print(f"League {args.league_id} not found — nothing to delete")
        else:
            print(f"Error deleting league: {e.detail}")
            sys.exit(1)
