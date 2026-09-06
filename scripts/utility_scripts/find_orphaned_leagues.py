"""
find_orphaned_leagues.py

Finds (and optionally cleans up) "orphaned" league records left behind when the
*same* league was onboarded twice within a narrow window — the check-then-act race
in ``POST /onboard``.

Background
----------
On a fresh ONBOARD the onboarder mints a brand-new ``canonical_league_id`` (a
UUID) and writes, in one transaction:

  * a METADATA item at ``PK = LEAGUE#{canonical_id}, SK = METADATA``
  * a LEAGUE_LOOKUP item at ``PK = LEAGUE#{league_id}#PLATFORM#{platform}, SK = LEAGUE_LOOKUP``
    whose ``canonical_league_id`` attribute points back at the METADATA.

The METADATA PK is a fresh UUID every time, so two concurrent onboards never
collide there — both METADATA items (and both ``raw-api-data/{canonical_id}/``
S3 folders, and both sets of precomputed views) survive. But both LEAGUE_LOOKUP
writes target the *same* per-platform PK, so the second silently overwrites the
first (last-write-wins). The result:

  * two METADATA items / two S3 folders with identical data, but
  * exactly one LEAGUE_LOOKUP, pointing at whichever onboard finished last.

The earlier canonical id is now unreachable by the app (nothing maps to it). This
script identifies those orphans and can delete the orphan's DynamoDB items + S3
data, leaving the live (referenced) league untouched.

What counts as an orphan
------------------------
A ``canonical_league_id`` that has a METADATA item but is referenced by **no**
LEAGUE_LOOKUP item. Each orphan is then classified:

  * ``DUPLICATE``  — a live (referenced) league exists on the *same platform*
    whose ``onboarded_at`` is within ``--window-seconds`` of the orphan's. This is
    the race fingerprint. With ``--verify-s3`` a time-matched twin is downgraded to
    ``UNMATCHED`` unless the two leagues' ``raw-api-data`` season files are
    byte-identical — so point the script at the right bucket (see below), or the
    comparison sees no objects and every twin looks non-identical.
  * ``UNMATCHED``  — an orphan with no such twin. Could be a half-finished delete
    or some other anomaly; **not** deleted unless you pass ``--include-unmatched``.

Safety
------
Dry-run by default — it only reports. ``--execute`` deletes, and before deleting
each orphan it re-checks GSI1 to confirm no LEAGUE_LOOKUP points at it (so a league
that became live between the scan and the delete is never touched). The landing-page
league count is derived hourly from the surviving METADATA items (the sync-counts
worker), so deleting an orphan needs no separate count adjustment.

Environment & names
-------------------
Pass ``--environment dev|prod`` (default ``dev``) and the script derives both names
from the Terraform convention in ``infrastructure/regional/main.tf``:

  * table  -> ``leagueql-table-{env}``
  * bucket -> ``leagueql-{env}-bucket-east-{AWS_ACCOUNT_ID}`` (the primary east bucket
    that holds ``raw-api-data``)

Deriving these together makes it impossible to read one environment's table against
another's bucket (the bug that made every orphan look like it had 0 S3 objects). The
east bucket needs ``AWS_ACCOUNT_ID`` in the environment; ``--table`` / ``--bucket``
override the derivation if you ever need a non-standard name.

Usage
-----
    # Dry-run against dev (default)
    pipenv run python scripts/utility_scripts/find_orphaned_leagues.py

    # Byte-verify S3 data before classifying as a duplicate
    pipenv run python scripts/utility_scripts/find_orphaned_leagues.py --verify-s3

    # Run against prod and actually delete (AWS_ACCOUNT_ID must be set)
    AWS_ACCOUNT_ID=<account-id> \
        pipenv run python scripts/utility_scripts/find_orphaned_leagues.py \
        --environment prod --verify-s3 --execute
"""

import argparse
import datetime
import hashlib
import logging
import os
import sys

import boto3
from boto3.dynamodb.conditions import Attr, Key

# Table / bucket names are derived from the target --environment so they can never
# be mismatched (the raw data lives in the *primary* east bucket). These mirror the
# Terraform naming in infrastructure/regional/main.tf. The east bucket needs the AWS
# account id, read from AWS_ACCOUNT_ID; --table / --bucket override the derivation.
TABLE_NAME_FMT = "leagueql-table-{env}"
BUCKET_NAME_FMT = "leagueql-{env}-bucket-east-{account_id}"

S3_PREFIX_FMT = "raw-api-data/{canonical_id}/"


def resolve_table(args) -> str:
    """The DynamoDB table name: explicit --table, else derived from --environment."""
    return args.table or TABLE_NAME_FMT.format(env=args.environment)


def resolve_bucket(args) -> str:
    """
    The raw-api-data S3 bucket: explicit --bucket, else derived from --environment.

    Returns an empty string when derivation is needed but AWS_ACCOUNT_ID is unset, so
    the caller can fail with a clear message.
    """
    if args.bucket:
        return args.bucket
    account_id = os.environ.get("AWS_ACCOUNT_ID", "")
    if not account_id:
        return ""
    return BUCKET_NAME_FMT.format(env=args.environment, account_id=account_id)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_timestamp(value: str) -> datetime.datetime:
    """Parses an ISO 8601 timestamp, tolerating a trailing ``Z`` for UTC."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def scan_leagues(table) -> tuple[dict, dict]:
    """
    Scans the table once, collecting every METADATA and LEAGUE_LOOKUP item.

    Args:
        table: A boto3 DynamoDB ``Table`` resource.

    Returns:
        A tuple ``(metadata, referenced)`` where:
          * ``metadata`` maps ``canonical_id`` -> ``{"platform", "onboarded_at"}``
            for every METADATA item, and
          * ``referenced`` maps a referenced ``canonical_id`` -> list of
            ``{"league_id", "platform"}`` from each LEAGUE_LOOKUP pointing at it.
    """
    metadata: dict[str, dict] = {}
    referenced: dict[str, list[dict]] = {}

    kwargs: dict = {
        "FilterExpression": Attr("SK").is_in(["METADATA", "LEAGUE_LOOKUP"]),
        "ProjectionExpression": "PK, SK, canonical_league_id, platform, onboarded_at, league_id",
    }
    while True:
        response = table.scan(**kwargs)
        for item in response.get("Items", []):
            if item["SK"] == "METADATA":
                pk = item["PK"]
                # METADATA PK is always LEAGUE#{canonical_id}; skip anything that
                # looks like a per-platform PK (defensive — shouldn't happen).
                if not pk.startswith("LEAGUE#") or "#PLATFORM#" in pk:
                    continue
                canonical_id = pk[len("LEAGUE#") :]
                metadata[canonical_id] = {
                    "platform": item.get("platform"),
                    "onboarded_at": item.get("onboarded_at"),
                }
            else:  # LEAGUE_LOOKUP
                canonical_id = item.get("canonical_league_id")
                if not canonical_id:
                    continue
                referenced.setdefault(canonical_id, []).append(
                    {
                        "league_id": item.get("league_id"),
                        "platform": item.get("platform"),
                    }
                )
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    return metadata, referenced


def find_twin(
    orphan_id: str, metadata: dict, referenced: dict, window_seconds: int
) -> str | None:
    """
    Finds a live (referenced) league that looks like the orphan's onboard twin.

    A twin shares the orphan's platform and was onboarded within ``window_seconds``
    of it — the fingerprint of the concurrent double-onboard race. When several
    qualify, the closest by onboard time wins.

    Args:
        orphan_id: The orphan's canonical league ID.
        metadata: The ``canonical_id`` -> metadata map from :func:`scan_leagues`.
        referenced: The referenced-canonical map from :func:`scan_leagues`.
        window_seconds: Max allowed gap between the two ``onboarded_at`` times.

    Returns:
        The twin's canonical league ID, or ``None`` if no candidate qualifies.
    """
    orphan_meta = metadata[orphan_id]
    orphan_ts_raw = orphan_meta.get("onboarded_at")
    if not orphan_ts_raw:
        return None
    orphan_ts = parse_timestamp(orphan_ts_raw)

    best: tuple[float, str] | None = None
    for live_id in referenced:
        live_meta = metadata.get(live_id)
        if not live_meta or live_id == orphan_id:
            continue
        if live_meta.get("platform") != orphan_meta.get("platform"):
            continue
        live_ts_raw = live_meta.get("onboarded_at")
        if not live_ts_raw:
            continue
        delta = abs((parse_timestamp(live_ts_raw) - orphan_ts).total_seconds())
        if delta <= window_seconds and (best is None or delta < best[0]):
            best = (delta, live_id)

    return best[1] if best else None


def collect_pk_keys(table, pk: str) -> list[dict]:
    """Returns the ``{PK, SK}`` keys of every item under a partition key."""
    keys: list[dict] = []
    kwargs: dict = {
        "KeyConditionExpression": Key("PK").eq(pk),
        "ProjectionExpression": "PK, SK",
        "ConsistentRead": True,
    }
    while True:
        response = table.query(**kwargs)
        keys.extend({"PK": i["PK"], "SK": i["SK"]} for i in response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return keys
        kwargs["ExclusiveStartKey"] = last_key


def has_live_lookup(table, canonical_id: str) -> bool:
    """
    True if any LEAGUE_LOOKUP currently points at this canonical id (via GSI1).

    Used as a guard immediately before deletion: if this returns True the league
    is live, not orphaned, and must not be touched.
    """
    response = table.query(
        IndexName="GSI1",
        KeyConditionExpression=Key("canonical_league_id").eq(canonical_id),
        FilterExpression=Attr("SK").eq("LEAGUE_LOOKUP"),
        ProjectionExpression="PK, SK",
    )
    return bool(response.get("Items"))


def list_s3_keys(s3, bucket: str, prefix: str) -> list[str]:
    """Returns every object key under an S3 prefix (paginated)."""
    keys: list[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def season_fingerprint(s3, bucket: str, canonical_id: str) -> dict[str, str]:
    """
    Returns ``{season_filename: sha256}`` for a league's raw season files.

    Only the ``{season}.json`` payloads are hashed; ``manifest.json`` is skipped
    because it carries a per-onboard ``correlation_id`` in its object metadata.
    """
    prefix = S3_PREFIX_FMT.format(canonical_id=canonical_id)
    fingerprint: dict[str, str] = {}
    for key in list_s3_keys(s3, bucket, prefix):
        name = key[len(prefix) :]
        if name == "manifest.json" or not name.endswith(".json"):
            continue
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        fingerprint[name] = hashlib.sha256(body).hexdigest()
    return fingerprint


def delete_dynamo_items(table, keys: list[dict]) -> None:
    """Batch-deletes the given ``{PK, SK}`` keys."""
    with table.batch_writer() as writer:
        for key in keys:
            writer.delete_item(Key=key)


def delete_s3_prefix(s3, bucket: str, keys: list[str]) -> None:
    """Deletes the given S3 object keys in batches of 1000."""
    for start in range(0, len(keys), 1000):
        batch = keys[start : start + 1000]
        s3.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
        )


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=(
            "Find (and optionally delete) orphaned league records left by the "
            "double-onboard race. Dry-run unless --execute is passed."
        )
    )
    p.add_argument(
        "--environment",
        "--env",
        dest="environment",
        choices=("dev", "prod"),
        default="dev",
        help="Target environment; derives the table and bucket names (default: dev).",
    )
    p.add_argument(
        "--table",
        default=None,
        help="Override the DynamoDB table name (default: derived from --environment).",
    )
    p.add_argument(
        "--bucket",
        default=None,
        help="Override the raw-api-data S3 bucket (default: derived from --environment).",
    )
    p.add_argument("--region", default=None, help="AWS region (optional).")
    p.add_argument(
        "--window-seconds",
        type=int,
        default=120,
        help="Max onboard-time gap to treat a live league as the orphan's twin (default: 120).",
    )
    p.add_argument(
        "--verify-s3",
        action="store_true",
        help="Confirm DUPLICATE classification by byte-comparing S3 season files.",
    )
    p.add_argument(
        "--include-unmatched",
        action="store_true",
        help="Also delete UNMATCHED orphans (no twin found). Use with care.",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete. Without this the script is dry-run.",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt before deleting.",
    )
    p.add_argument("--debug", action="store_true", help="Enable DEBUG logging.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Resolve table/bucket up front so the rest of the run uses consistent names.
    args.table = resolve_table(args)
    args.bucket = resolve_bucket(args)
    if not args.bucket:
        logger.error(
            "Could not derive the %s bucket: set AWS_ACCOUNT_ID or pass --bucket.",
            args.environment,
        )
        sys.exit(1)
    logger.info(
        "Environment=%s -> table=%s bucket=%s",
        args.environment,
        args.table,
        args.bucket,
    )

    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    table = session.resource("dynamodb").Table(args.table)
    s3 = session.client("s3")

    logger.info("Scanning table %s for METADATA + LEAGUE_LOOKUP items...", args.table)
    metadata, referenced = scan_leagues(table)
    logger.info(
        "Found %d league(s) with METADATA; %d canonical id(s) referenced by a LEAGUE_LOOKUP",
        len(metadata),
        len(referenced),
    )

    orphan_ids = sorted(cid for cid in metadata if cid not in referenced)
    if not orphan_ids:
        logger.info("No orphaned leagues found. Nothing to do.")
        return

    logger.info(
        "Found %d orphaned canonical id(s) (METADATA but no LEAGUE_LOOKUP).",
        len(orphan_ids),
    )

    # Classify each orphan and gather its blast radius so the dry-run shows exactly
    # what would be deleted.
    plans: list[dict] = []
    for orphan_id in orphan_ids:
        twin_id = find_twin(orphan_id, metadata, referenced, args.window_seconds)
        classification = "DUPLICATE" if twin_id else "UNMATCHED"

        s3_match = None
        if twin_id and args.verify_s3:
            orphan_fp = season_fingerprint(s3, args.bucket, orphan_id)
            twin_fp = season_fingerprint(s3, args.bucket, twin_id)
            s3_match = orphan_fp == twin_fp and bool(orphan_fp)
            if not s3_match:
                # A twin by time but not by data — downgrade so it isn't auto-deleted.
                classification = "UNMATCHED"

        dynamo_keys = collect_pk_keys(table, f"LEAGUE#{orphan_id}")
        s3_keys = list_s3_keys(
            s3, args.bucket, S3_PREFIX_FMT.format(canonical_id=orphan_id)
        )
        plans.append(
            {
                "orphan_id": orphan_id,
                "classification": classification,
                "twin_id": twin_id,
                "s3_match": s3_match,
                "dynamo_keys": dynamo_keys,
                "s3_keys": s3_keys,
                "meta": metadata[orphan_id],
            }
        )

    for plan in plans:
        meta = plan["meta"]
        twin_note = ""
        if plan["twin_id"]:
            twin_meta = metadata.get(plan["twin_id"], {})
            twin_note = f" twin={plan['twin_id']} (live, onboarded {twin_meta.get('onboarded_at')})"
            if plan["s3_match"] is not None:
                twin_note += f" s3_identical={plan['s3_match']}"
        logger.info(
            "[%s] orphan=%s platform=%s onboarded=%s dynamo_items=%d s3_objects=%d%s",
            plan["classification"],
            plan["orphan_id"],
            meta.get("platform"),
            meta.get("onboarded_at"),
            len(plan["dynamo_keys"]),
            len(plan["s3_keys"]),
            twin_note,
        )

    deletable = [
        p
        for p in plans
        if p["classification"] == "DUPLICATE"
        or (p["classification"] == "UNMATCHED" and args.include_unmatched)
    ]
    skipped = len(plans) - len(deletable)
    if skipped:
        logger.info(
            "%d UNMATCHED orphan(s) will be left in place (pass --include-unmatched to delete).",
            skipped,
        )

    if not args.execute:
        logger.info(
            "Dry-run: %d orphan(s) would be deleted. Re-run with --execute to delete.",
            len(deletable),
        )
        return

    if not deletable:
        logger.info("Nothing to delete.")
        return

    if not args.yes:
        prompt = (
            f"\nAbout to DELETE {len(deletable)} orphaned league(s) from table "
            f"'{args.table}' and bucket '{args.bucket}'.\nType 'delete' to proceed: "
        )
        if input(prompt).strip().lower() != "delete":
            logger.info("Aborted by user.")
            return

    deleted = 0
    for plan in deletable:
        orphan_id = plan["orphan_id"]
        # Guard: never delete a league that became live since the scan.
        if has_live_lookup(table, orphan_id):
            logger.warning(
                "SKIP %s: a LEAGUE_LOOKUP now points at it (no longer orphaned).",
                orphan_id,
            )
            continue
        logger.info(
            "Deleting orphan %s: %d DynamoDB item(s), %d S3 object(s)",
            orphan_id,
            len(plan["dynamo_keys"]),
            len(plan["s3_keys"]),
        )
        delete_dynamo_items(table, plan["dynamo_keys"])
        delete_s3_prefix(s3, args.bucket, plan["s3_keys"])
        deleted += 1

    logger.info("Done: %d orphan(s) deleted.", deleted)


if __name__ == "__main__":
    main()
