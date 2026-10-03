"""
backfill_league_members.py

Seeds the per-user league membership index (backend/user-leagues) for leagues onboarded before
``GET /me/leagues`` shipped, so their owners and invited members see them under "View My Leagues"
without doing anything.

How it works
------------
Every METADATA item is listed through the sparse GSI3 all-leagues index (``SK = "METADATA"``,
paginated). For each league, a MEMBER item (``LEAGUE#{canonical}`` / ``MEMBER#{clerk_user_id}``)
is written for ``owner_user_id`` and for every user in ``members``, with
``joined_at = onboarded_at``. Writes go through the same conditional put the API uses
(``common.league_members.put_league_member``), so the script is idempotent. Re-running it
creates nothing new and never changes an existing ``joined_at``.

Sleeper leagues opened before this shipped can't be recovered (viewers were never recorded).
They appear in a user's list the next time that user opens the league.

Run it **after** GSI4 exists (infra applied) and the backend is deployed, so no new
onboard/invite slips between the backfill and the code that maintains the index.

Environment & names
-------------------
Pass ``--environment dev|prod`` (default ``dev``). The table name is derived from the Terraform
convention (``leagueql-table-{env}``); ``--table`` overrides it.

Usage
-----
    # Dry-run against dev (default): reports what would be written
    pipenv run python scripts/utility_scripts/backfill_league_members.py

    # Write the index in prod
    pipenv run python scripts/utility_scripts/backfill_league_members.py \
        --environment prod --execute
"""

import argparse
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

# Make the shared ``common`` package importable so we reuse the exact MEMBER item shape and
# conditional put the API uses, rather than duplicating it.
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

from common.league_members import put_league_member

TABLE_NAME_FMT = "leagueql-table-{env}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def resolve_table(args) -> str:
    """The DynamoDB table name: explicit --table, else derived from --environment."""
    return args.table or TABLE_NAME_FMT.format(env=args.environment)


def iter_metadata(table: Any) -> Iterator[dict]:
    """Yield every METADATA item via the sparse GSI3 index (paginated)."""
    kwargs: dict[str, Any] = {
        "IndexName": "GSI3",
        "KeyConditionExpression": Key("SK").eq("METADATA"),
    }
    while True:
        response = table.query(**kwargs)
        yield from response.get("Items", [])
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return
        kwargs["ExclusiveStartKey"] = last_key


def league_users(table: Any, metadata: dict) -> set[str]:
    """Return the owner plus every member of a league.

    GSI3 doesn't project ``members``, so the full METADATA item is read for it.
    """
    item = (
        table.get_item(
            Key={"PK": metadata["PK"], "SK": "METADATA"},
            ProjectionExpression="owner_user_id, members",
        ).get("Item")
        or {}
    )
    users = set(item.get("members") or set())
    if item.get("owner_user_id"):
        users.add(item["owner_user_id"])
    return users


def backfill(table: Any, execute: bool) -> dict[str, int]:
    """Index every league's owner and members.

    Args:
        table: A boto3 DynamoDB ``Table`` resource.
        execute: Write the items; when False, only count what would be written.

    Returns:
        Counts: ``leagues`` scanned, ``created`` (or would-create on a dry run), and
        ``skipped`` (already indexed; always 0 on a dry run).
    """
    counts = {"leagues": 0, "created": 0, "skipped": 0}
    for metadata in iter_metadata(table):
        counts["leagues"] += 1
        canonical_league_id = metadata["PK"].removeprefix("LEAGUE#")
        for user_id in sorted(league_users(table, metadata)):
            if not execute:
                logger.info(
                    "[dry-run] would index %s in %s", user_id, canonical_league_id
                )
                counts["created"] += 1
                continue
            if put_league_member(
                table, canonical_league_id, user_id, metadata.get("onboarded_at")
            ):
                counts["created"] += 1
            else:
                counts["skipped"] += 1
    return counts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("--environment", choices=["dev", "prod"], default="dev")
    parser.add_argument("--table", help="Override the derived DynamoDB table name")
    parser.add_argument(
        "--execute", action="store_true", help="Write items (default: dry-run)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, int]:
    args = parse_args(argv)
    table_name = resolve_table(args)
    logger.info(
        "Backfilling league membership index in %s (%s)",
        table_name,
        "EXECUTE" if args.execute else "dry-run",
    )
    table = boto3.resource("dynamodb").Table(table_name)
    counts = backfill(table, args.execute)
    logger.info(
        "Done: %d league(s), %d %s, %d already indexed",
        counts["leagues"],
        counts["created"],
        "created" if args.execute else "would be created",
        counts["skipped"],
    )
    return counts


if __name__ == "__main__":
    main()
