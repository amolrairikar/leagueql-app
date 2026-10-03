"""Shared per-user league membership index writes for LeagueQL (backend/user-leagues).

One MEMBER item per (league, user) lets ``GET /me/leagues`` list a user's leagues with a
single query on the sparse GSI4 index:

    PK = LEAGUE#{canonical_league_id}
    SK = MEMBER#{clerk_user_id}
    member_user_id = {clerk_user_id}   (GSI4 HASH)
    joined_at = ISO 8601 (UTC)         (GSI4 RANGE)

The item lives in the league's own partition, so deleting the league removes it, and a
platform migration (which keeps the canonical id) leaves it alone. It is a read index for
listing only — authorization still reads METADATA ``owner_user_id`` / ``members``.

Every write is a conditional put on ``attribute_not_exists(PK)``, so writes are idempotent and
``joined_at`` records the first time the user was indexed.

Vendored into every function's deployment zip via the build script.
"""

import datetime
from typing import Any

import botocore.exceptions

MEMBER_SK_PREFIX = "MEMBER#"
MEMBER_INDEX_NAME = "GSI4"
_NOT_INDEXED = "attribute_not_exists(PK)"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def member_item(
    canonical_league_id: str, clerk_user_id: str, joined_at: str | None = None
) -> dict[str, str]:
    """Build a MEMBER item in the boto3 resource (plain-value) shape.

    Args:
        canonical_league_id: The canonical league ID.
        clerk_user_id: The Clerk user ID being indexed.
        joined_at: ISO 8601 join time; defaults to now (UTC).

    Returns:
        The item dict, ready for ``Table.put_item``.
    """
    return {
        "PK": f"LEAGUE#{canonical_league_id}",
        "SK": f"{MEMBER_SK_PREFIX}{clerk_user_id}",
        "member_user_id": clerk_user_id,
        "joined_at": joined_at or _now_iso(),
    }


def member_transact_put(
    table_name: str,
    canonical_league_id: str,
    clerk_user_id: str,
    joined_at: str | None = None,
) -> dict[str, Any]:
    """Build a low-level ``TransactWriteItems`` Put entry for a MEMBER item.

    Used by the onboarder so the owner is indexed atomically with the league's first
    METADATA write. Unlike ``put_league_member`` this Put is unconditional: the METADATA
    Put in the same transaction is unconditional too, and a retried onboard (async Lambda
    retry with the same canonical id) must not have its whole transaction cancelled by an
    already-written MEMBER item.

    Args:
        table_name: The DynamoDB table name.
        canonical_league_id: The canonical league ID.
        clerk_user_id: The Clerk user ID being indexed.
        joined_at: ISO 8601 join time; defaults to now (UTC).

    Returns:
        A ``{"Put": {...}}`` transaction entry in the typed attribute-value shape.
    """
    item = member_item(canonical_league_id, clerk_user_id, joined_at)
    return {
        "Put": {
            "TableName": table_name,
            "Item": {k: {"S": v} for k, v in item.items()},
        }
    }


def put_league_member(
    table: Any,
    canonical_league_id: str,
    clerk_user_id: str,
    joined_at: str | None = None,
) -> bool:
    """Index ``clerk_user_id`` as a member of a league, if not already indexed.

    Args:
        table: A boto3 DynamoDB ``Table`` resource.
        canonical_league_id: The canonical league ID.
        clerk_user_id: The Clerk user ID being indexed.
        joined_at: ISO 8601 join time; defaults to now (UTC).

    Returns:
        True if a new item was written, False if the user was already indexed.

    Raises:
        botocore.exceptions.ClientError: Any DynamoDB error other than the item
            already existing.
    """
    try:
        table.put_item(
            Item=member_item(canonical_league_id, clerk_user_id, joined_at),
            ConditionExpression=_NOT_INDEXED,
        )
    except botocore.exceptions.ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        raise
    return True
