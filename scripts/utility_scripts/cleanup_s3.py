"""
s3_cleanup_delete_markers.py

Permanently removes all versions of S3 objects whose latest version is a delete
marker — covering both objects expired by lifecycle policy (orphaned markers) and
objects explicitly deleted while older versions still exist.

Usage:
    # Activate the pipenv shell first (run once per session)
    pipenv shell

    # Dry-run (default) — prints what would be deleted
    pipenv run python deployment_scripts/cleanup_s3.py --bucket my-bucket

    # Actually delete
    pipenv run python deployment_scripts/cleanup_s3.py --bucket my-bucket --execute

    # Scope to a key prefix
    pipenv run python deployment_scripts/cleanup_s3.py --bucket my-bucket --prefix logs/ --execute

    # Use a non-default AWS profile
    pipenv run python deployment_scripts/cleanup_s3.py --bucket my-bucket --profile prod --execute
"""

import argparse
import logging
import sys
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 1_000  # S3 delete API accepts up to 1 000 objects per call


def iter_versions(s3_client, bucket: str, prefix: str):
    """Yield every version/delete-marker page for the bucket+prefix."""
    paginator = s3_client.get_paginator("list_object_versions")
    page_cfg = {"Bucket": bucket}
    if prefix:
        page_cfg["Prefix"] = prefix

    for page in paginator.paginate(**page_cfg):
        yield page


def collect_deleted_objects(s3_client, bucket: str, prefix: str) -> list[dict]:
    """
    Return all versions (delete markers + data versions) for keys whose latest
    version is a delete marker.

    Strategy
    --------
    Stream all versions and delete-markers in a single paginated pass.
    Track, per key:
      - all non-marker versions (so they can be deleted alongside the marker)
      - each delete marker and whether it is the latest version

    After the full scan, any key with IsLatest=True on a delete marker is
    included. Both the markers and any underlying data versions are returned
    so the key is fully removed from the bucket.
    """
    key_data: dict[str, dict] = defaultdict(lambda: {"markers": [], "versions": []})

    page_count = 0
    for page in iter_versions(s3_client, bucket, prefix):
        page_count += 1
        if page_count % 10 == 0:
            logger.info("Scanned %d pages so far…", page_count)

        for v in page.get("Versions", []):
            key_data[v["Key"]]["versions"].append(
                {"Key": v["Key"], "VersionId": v["VersionId"]}
            )

        for dm in page.get("DeleteMarkers", []):
            key_data[dm["Key"]]["markers"].append(
                {
                    "Key": dm["Key"],
                    "VersionId": dm["VersionId"],
                    "IsLatest": dm.get("IsLatest", False),
                    "LastModified": dm.get("LastModified"),
                }
            )

    to_delete = []
    matched_keys = 0
    for key, data in key_data.items():
        if any(m["IsLatest"] for m in data["markers"]):
            matched_keys += 1
            to_delete.extend(data["markers"])
            to_delete.extend(data["versions"])

    logger.info(
        "Scan complete: %d unique keys, %d key(s) with delete marker as latest version (%d object(s) to remove).",
        len(key_data),
        matched_keys,
        len(to_delete),
    )
    return to_delete


def batch_delete(s3_client, bucket: str, objects: list[dict], dry_run: bool) -> int:
    """
    Delete objects in batches of BATCH_SIZE.
    Returns the total number of successfully deleted objects.
    """
    deleted_count = 0
    errors = []

    for i in range(0, len(objects), BATCH_SIZE):
        batch = objects[i : i + BATCH_SIZE]
        payload = [{"Key": o["Key"], "VersionId": o["VersionId"]} for o in batch]

        if dry_run:
            for o in batch:
                logger.info(
                    "[DRY-RUN] Would delete  key=%s  version=%s",
                    o["Key"],
                    o["VersionId"],
                )
            deleted_count += len(batch)
            continue

        try:
            resp = s3_client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": payload, "Quiet": False},
            )
        except ClientError as exc:
            logger.error("delete_objects API call failed: %s", exc)
            raise

        for d in resp.get("Deleted", []):
            logger.debug("Deleted  key=%s  version=%s", d["Key"], d["VersionId"])
        deleted_count += len(resp.get("Deleted", []))

        for e in resp.get("Errors", []):
            logger.error(
                "Failed to delete  key=%s  version=%s  code=%s  msg=%s",
                e["Key"],
                e.get("VersionId"),
                e["Code"],
                e["Message"],
            )
            errors.append(e)

    if errors:
        logger.warning(
            "%d object(s) could not be deleted (see errors above).", len(errors)
        )

    return deleted_count


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Remove orphaned S3 delete markers (objects expired by lifecycle policy)."
    )
    p.add_argument("--bucket", required=True, help="Target S3 bucket name")
    p.add_argument(
        "--prefix", default="", help="Limit scan to this key prefix (optional)"
    )
    p.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Actually delete. Without this flag the script runs in dry-run mode.",
    )
    p.add_argument("--profile", default=None, help="AWS CLI profile name (optional)")
    p.add_argument(
        "--region", default=None, help="AWS region (optional, falls back to env/config)"
    )
    p.add_argument("--debug", action="store_true", help="Enable DEBUG logging")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    dry_run = not args.execute
    mode_label = "DRY-RUN" if dry_run else "EXECUTE"
    logger.info(
        "Mode: %s | Bucket: %s | Prefix: %r", mode_label, args.bucket, args.prefix
    )

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    s3 = session.client("s3")

    # Verify bucket is versioning-enabled — delete markers only exist on versioned buckets
    try:
        ver = s3.get_bucket_versioning(Bucket=args.bucket)
        status = ver.get("Status", "Disabled")
        if status not in ("Enabled", "Suspended"):
            logger.error(
                "Bucket '%s' does not have versioning enabled (status=%s). "
                "Delete markers cannot exist here.",
                args.bucket,
                status,
            )
            sys.exit(1)
        logger.info("Bucket versioning status: %s", status)
    except ClientError as exc:
        logger.error("Could not check versioning for bucket '%s': %s", args.bucket, exc)
        sys.exit(1)

    objects_to_delete = collect_deleted_objects(s3, args.bucket, args.prefix)

    if not objects_to_delete:
        logger.info(
            "Nothing to do — no keys with a delete marker as the latest version."
        )
        return

    logger.info(
        "%s %d object(s) across deleted keys…",
        "Would delete" if dry_run else "Deleting",
        len(objects_to_delete),
    )

    deleted = batch_delete(s3, args.bucket, objects_to_delete, dry_run=dry_run)

    if dry_run:
        logger.info(
            "Dry-run complete. %d object(s) would have been deleted. Re-run with --execute to apply.",
            deleted,
        )
    else:
        logger.info("Done. %d object(s) deleted.", deleted)


if __name__ == "__main__":
    main()
