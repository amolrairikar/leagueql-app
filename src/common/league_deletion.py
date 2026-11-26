"""Shared league deletion for the API's manual delete and the league reaper.

Used by ``DELETE /leagues/{leagueId}`` (backend/delete-league) and the nightly unused-league
reaper (backend/league-reaper). AWS clients are injected so each caller supplies its own.

Vendored into every function's deployment zip via the build script.
"""

import time
from collections.abc import Callable, Collection, Iterator
from typing import Any

from boto3.dynamodb.conditions import Attr, Key

from common.logging_utils import logger

# S3 delete_objects accepts at most 1,000 keys, which is also the list_objects_v2 page size.
_S3_DELETE_MAX_KEYS = 1000


class LeagueDeletionError(Exception):
    """A league's data could not be fully removed."""


class OrphanedItemsError(LeagueDeletionError):
    """DynamoDB items remained after every delete pass.

    Attributes:
        remaining_sks: Sort keys of the items still present.
    """

    def __init__(self, canonical_league_id: str, remaining_sks: list[str]):
        super().__init__(
            f"Orphaned items remain for league {canonical_league_id}: {remaining_sks}"
        )
        self.remaining_sks = remaining_sks


def query_all_keys(table: Any, query_kwargs: dict) -> list[dict]:
    """Run a paginated query, returning every matched item's {PK, SK} key.

    Args:
        table: A boto3 DynamoDB ``Table`` resource.
        query_kwargs: Keyword arguments passed to table.query (must project PK/SK).

    Returns:
        A list of {"PK", "SK"} key dicts across all result pages.
    """
    keys: list[dict] = []
    kwargs = dict(query_kwargs)
    while True:
        response = table.query(**kwargs)
        for item in response.get("Items", []):
            keys.append({"PK": item["PK"], "SK": item["SK"]})
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return keys
        kwargs["ExclusiveStartKey"] = last_key


def collect_league_keys(table: Any, canonical_league_id: str) -> list[dict]:
    """Collect the keys of every DynamoDB item belonging to a league.

    This covers two key spaces:
      * everything under the canonical PK (METADATA and all precomputed views,
        including any future SK types) read with strong consistency, and
      * the LEAGUE_LOOKUP items, which live under their own per-platform PKs and
        are located via GSI1 (eventually consistent).

    Args:
        table: A boto3 DynamoDB ``Table`` resource.
        canonical_league_id: The canonical league ID.

    Returns:
        A list of {"PK", "SK"} key dicts for every item owned by the league.
    """
    keys = query_all_keys(
        table,
        {
            "KeyConditionExpression": Key("PK").eq(f"LEAGUE#{canonical_league_id}"),
            "ProjectionExpression": "PK, SK",
            "ConsistentRead": True,
        },
    )
    keys += query_all_keys(
        table,
        {
            "IndexName": "GSI1",
            "KeyConditionExpression": Key("canonical_league_id").eq(
                canonical_league_id
            ),
            "ProjectionExpression": "PK, SK",
        },
    )
    return keys


def _delete_until_gone(
    table: Any,
    canonical_league_id: str,
    should_delete: Callable[[dict], bool],
    max_attempts: int,
) -> None:
    """Delete the league's matching items, re-verifying until none remain.

    Raises:
        OrphanedItemsError: If matching items remain after ``max_attempts`` passes.
    """

    def _matching_keys() -> list[dict]:
        return [
            key
            for key in collect_league_keys(table, canonical_league_id)
            if should_delete(key)
        ]

    for attempt in range(1, max_attempts + 1):
        keys = _matching_keys()
        if not keys:
            return
        logger.info(
            "Delete attempt %d/%d: removing %d items for %s",
            attempt,
            max_attempts,
            len(keys),
            canonical_league_id,
        )
        with table.batch_writer() as writer:
            for key in keys:
                writer.delete_item(Key=key)
        time.sleep(0.5 * attempt)  # let GSI1 catch up before re-verifying

    remaining = _matching_keys()
    if remaining:
        raise OrphanedItemsError(canonical_league_id, [key["SK"] for key in remaining])


def delete_all_league_items(
    table: Any, canonical_league_id: str, max_attempts: int = 4
) -> None:
    """Delete every DynamoDB item for a league, removing METADATA last.

    Rather than deleting a hardcoded set of SK prefixes, this discovers the
    league's actual items on each pass and deletes them, then re-verifies. This
    catches orphaned items (e.g. PLATFORM_MIGRATION#) regardless of SK type and
    tolerates GSI1 eventual-consistency lag on LEAGUE_LOOKUP items.

    METADATA is only removed once everything else is verified gone: it is what lists
    a league in GSI3, so a partially failed removal stays discoverable by the league
    reaper and is retried.

    Args:
        table: A boto3 DynamoDB ``Table`` resource.
        canonical_league_id: The canonical league ID.
        max_attempts: Number of delete+verify passes per phase before giving up.

    Raises:
        OrphanedItemsError: If items still remain after ``max_attempts``.
    """
    _delete_until_gone(
        table, canonical_league_id, lambda key: key["SK"] != "METADATA", max_attempts
    )
    _delete_until_gone(table, canonical_league_id, lambda key: True, max_attempts)


def delete_league_raw_data(
    s3_client: Any, bucket: str, canonical_league_id: str
) -> int:
    """Delete every raw API payload under the league's S3 prefix.

    Args:
        s3_client: A boto3 S3 client.
        bucket: The bucket holding the raw payloads.
        canonical_league_id: The canonical league ID.

    Returns:
        The number of objects deleted.

    Raises:
        LeagueDeletionError: If S3 reports that any object could not be deleted.
        botocore.exceptions.ClientError: On an S3 request error.
    """
    list_kwargs: dict[str, Any] = {
        "Bucket": bucket,
        "Prefix": f"raw-api-data/{canonical_league_id}/",
        "MaxKeys": _S3_DELETE_MAX_KEYS,
    }
    deleted = 0
    while True:
        page = s3_client.list_objects_v2(**list_kwargs)
        keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if keys:
            response = s3_client.delete_objects(
                Bucket=bucket,
                # Quiet returns only the errors in the response.
                Delete={"Objects": keys, "Quiet": True},
            )
            errors = response.get("Errors")
            if errors:
                raise LeagueDeletionError(
                    f"Failed to delete {len(errors)} S3 objects for league "
                    f"{canonical_league_id}"
                )
            deleted += len(keys)
        if not page.get("IsTruncated"):
            return deleted
        list_kwargs["ContinuationToken"] = page["NextContinuationToken"]


def iter_owner_league_metadata(
    table: Any, owner_user_id: str, exclude_canonical_league_ids: Collection[str]
) -> Iterator[dict]:
    """Yield the GSI3 entry of every league the user owns, except the excluded ones.

    Scans GSI3 (the sparse all-METADATA index) with pagination, filtered to the owner's
    leagues. Excluding by PK also covers just-deleted leagues the eventually consistent
    index may still return.

    Args:
        table: A boto3 DynamoDB ``Table`` resource.
        owner_user_id: The owner whose leagues are enumerated.
        exclude_canonical_league_ids: Canonical ids of the leagues to skip.

    Yields:
        The projected METADATA item for each other owned league.
    """
    excluded_pks = {f"LEAGUE#{cid}" for cid in exclude_canonical_league_ids}
    kwargs: dict[str, Any] = {
        "IndexName": "GSI3",
        "KeyConditionExpression": Key("SK").eq("METADATA"),
        "FilterExpression": Attr("owner_user_id").eq(owner_user_id),
    }
    while True:
        response = table.query(**kwargs)
        for item in response.get("Items", []):
            if item.get("PK") in excluded_pks:
                continue
            yield item
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return
        kwargs["ExclusiveStartKey"] = last_key


def owner_has_other_yahoo_leagues(
    table: Any, owner_user_id: str, exclude_canonical_league_ids: Collection[str]
) -> bool:
    """Return whether the user owns a Yahoo league other than the excluded ones.

    The effective platform is ``active_platform`` falling back to ``platform``, so a
    league migrated *to* Yahoo counts and one migrated *away* from Yahoo does not.
    """
    return any(
        (item.get("active_platform") or item.get("platform")) == "YAHOO"
        for item in iter_owner_league_metadata(
            table, owner_user_id, exclude_canonical_league_ids
        )
    )


def owner_has_other_optedin_espn_leagues(
    table: Any, owner_user_id: str, exclude_canonical_league_ids: Collection[str]
) -> bool:
    """Return whether the user owns another ESPN league opted into auto-refresh.

    GSI3 does not project ``auto_refresh_enabled``, so each other ESPN league's METADATA
    item is read to check the flag.
    """
    for item in iter_owner_league_metadata(
        table, owner_user_id, exclude_canonical_league_ids
    ):
        if (item.get("active_platform") or item.get("platform")) != "ESPN":
            continue
        full = table.get_item(Key={"PK": item["PK"], "SK": "METADATA"}).get("Item", {})
        if full.get("auto_refresh_enabled"):
            return True
    return False
