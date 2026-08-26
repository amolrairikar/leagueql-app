import datetime
import json
import os
from typing import Any

import boto3
import botocore.config
import botocore.exceptions
from utils import correlation_id_var, logger

from common.tracing import inject_context

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_s3 = boto3.client("s3", config=_retry_config)
_dynamodb = boto3.client("dynamodb", config=_retry_config)


def upload_results_to_s3(
    results: list[dict[str, Any]],
    bucket_name: str,
    prefix: str,
    platform: str,
    reprocess_all: bool = False,
) -> None:
    """
    Uploads raw API data to S3 as per-season files plus a manifest.

    Groups results by season and writes one {season}.json per season, then
    writes manifest.json last (which is the S3 trigger target for the processor).

    Args:
        results: List containing raw API results.
        bucket_name: Name of the S3 bucket to upload data to.
        prefix: Key prefix within the S3 bucket (e.g. "raw-api-data/{league_id}").
        platform: The platform (e.g., ESPN, SLEEPER) that the league is on.
        reprocess_all: When True, stamps ``reprocess_all=true`` on the manifest metadata
            so the processor rebuilds every season's views instead of only the latest
            (backend/sleeper-transactions backfill). Default False.
    """
    try:
        seasons_data: dict[str, list[dict[str, Any]]] = {}
        for item in results:
            season = str(item["season"])
            seasons_data.setdefault(season, []).append(item)

        logger.info(
            "Uploading season files to S3: prefix=%s season_count=%d seasons=%s",
            prefix,
            len(seasons_data),
            sorted(seasons_data.keys()),
        )
        for season, season_results in seasons_data.items():
            s3_key = f"{prefix}/{season}.json"
            logger.info(
                "Writing S3 object: key=%s record_count=%d", s3_key, len(season_results)
            )
            _s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(season_results),
                ContentType="application/json",
            )

        manifest_key = f"{prefix}/manifest.json"
        try:
            existing_manifest_obj = _s3.get_object(Bucket=bucket_name, Key=manifest_key)
            logger.info(
                "Existing manifest found in S3, merging new seasons with existing manifest"
            )
            full_manifest = json.loads(existing_manifest_obj["Body"].read())
        except botocore.exceptions.ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                logger.info("No existing manifest found in S3, creating new manifest")
                full_manifest = {}
            else:
                logger.error(
                    "Error occurred while fetching existing manifest from S3: %s", e
                )
                raise

        existing_seasons = set(full_manifest.get(platform, []))
        new_seasons = set(seasons_data.keys())
        full_manifest[platform] = sorted(existing_seasons.union(new_seasons))

        metadata = {"correlation_id": correlation_id_var.get()}
        if reprocess_all:
            metadata["reprocess_all"] = "true"
        # Carry W3C trace context (traceparent/tracestate) in the object metadata so
        # the processor — triggered by this manifest's S3 event — continues the trace
        # (backend/otel-tracing). A no-op when tracing is disabled. S3 lowercases metadata keys and
        # the W3C header names are already lowercase, so the propagator round-trips.
        inject_context(metadata)

        _s3.put_object(
            Bucket=bucket_name,
            Key=f"{prefix}/manifest.json",
            Body=json.dumps(full_manifest),
            ContentType="application/json",
            Metadata=metadata,
        )
        logger.info("Wrote manifest to S3")
    except botocore.exceptions.ClientError as e:
        logger.error("Error occurred while writing raw API JSON to S3: %s", e)
        raise


def write_pending_league_lookup(
    league_id: str,
    platform: str,
    canonical_league_id: str,
    pending_season: str,
) -> None:
    """
    Register a renewed Sleeper season's league ID before its season has started.

    A renewed Sleeper league gets a brand-new league ID each season, but that season
    carries no usable data until it flips to ``in_season`` (backend/league-onboarding / backend/league-refresh). We still
    persist the new ID -> canonical mapping the moment the user hands it to us, because
    Sleeper only links seasons *backwards* (via ``previous_league_id``): without this
    record the scheduled auto-refresh could never discover the new season, and the
    association would be silently lost until a manual re-onboard.

    The item is written **without** a ``seasons`` set — an empty DynamoDB string set is
    invalid, and the not-yet-started season must not surface in any dropdown until it has
    data. A ``pending_season`` marker records which season we are waiting on; the
    scheduled Sleeper auto-refresh (backend/scheduled-sleeper-auto-refresh) polls pending lookups each run and the refresh
    promotes this item (adds ``seasons``, drops the marker) once the season starts.

    Args:
        league_id: The renewed season's new Sleeper league ID.
        platform: The platform (always ``SLEEPER`` for this path).
        canonical_league_id: The existing canonical league this renewal belongs to.
        pending_season: The not-yet-started season being awaited (e.g. ``"2026"``).
    """
    try:
        table_name = os.environ["DYNAMODB_TABLE_NAME"]
        logger.info(
            "Registering pending Sleeper season %s: league_id=%s canonical_league_id=%s",
            pending_season,
            league_id,
            canonical_league_id,
        )
        _dynamodb.put_item(
            TableName=table_name,
            Item={
                "PK": {"S": f"LEAGUE#{league_id}#PLATFORM#{platform}"},
                "SK": {"S": "LEAGUE_LOOKUP"},
                "canonical_league_id": {"S": canonical_league_id},
                "platform": {"S": platform},
                "league_id": {"S": league_id},
                "pending_season": {"S": pending_season},
            },
        )
    except KeyError:
        logger.error("Environment variable 'DYNAMODB_TABLE_NAME' not set!")
        raise
    except botocore.exceptions.ClientError as e:
        logger.error("Error occurred while writing pending LEAGUE_LOOKUP: %s", e)
        raise


def write_league_records(
    league_id: str,
    platform: str,
    canonical_league_id: str,
    seasons: list[str],
    request_type: str,
    is_new_season_refresh: bool = False,
    owner_user_id: str | None = None,
) -> None:
    """
    Writes the league's METADATA (on first onboard) and LEAGUE_LOOKUP records.

    Job status is tracked separately in the JOB_STATUS item (keyed by
    correlation_id), so this no longer writes any status attribute — it persists
    the league/season lookup records the rest of the pipeline and API rely on.

    Args:
        league_id: The ID for the league on its platform.
        platform: The platform (e.g., ESPN, SLEEPER) that the league is on.
        canonical_league_id: The unique ID for the league.
        seasons: List of strings representing number of seasons league was active for prior to onboarding.
        request_type: The type of onboarding request (e.g., "ONBOARD" or "REFRESH")
        is_new_season_refresh: If True, league_id is a new season's ID not yet in LEAGUE_LOOKUP;
            a new LEAGUE_LOOKUP item is created via Put instead of updating an existing one.
        owner_user_id: Clerk user ID of the onboarding owner (backend/league-authorization). On first
            ONBOARD it is recorded on METADATA and seeds the ``members`` set; REFRESH/MIGRATE
            never touch it, so the original owner and any verified members are preserved.
    """
    try:
        table_name = os.environ["DYNAMODB_TABLE_NAME"]
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if request_type == "MIGRATE":
            # Job status now lives in the JOB_STATUS item (keyed by correlation_id),
            # so the only METADATA write needed here is none — just the lookup.
            transact_items = [
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "PK": {"S": f"LEAGUE#{league_id}#PLATFORM#{platform}"},
                            "SK": {"S": "LEAGUE_LOOKUP"},
                            "canonical_league_id": {"S": canonical_league_id},
                            "seasons": {"SS": seasons},
                            "platform": {"S": platform},
                            "league_id": {"S": league_id},
                        },
                    }
                },
            ]
        elif request_type == "REFRESH":
            if is_new_season_refresh:
                league_lookup_operation = {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "PK": {"S": f"LEAGUE#{league_id}#PLATFORM#{platform}"},
                            "SK": {"S": "LEAGUE_LOOKUP"},
                            "canonical_league_id": {"S": canonical_league_id},
                            "seasons": {"SS": seasons},
                            "platform": {"S": platform},
                            "league_id": {"S": league_id},
                        },
                    }
                }
            else:
                league_lookup_operation = {
                    "Update": {
                        "TableName": table_name,
                        "Key": {
                            "PK": {"S": f"LEAGUE#{league_id}#PLATFORM#{platform}"},
                            "SK": {"S": "LEAGUE_LOOKUP"},
                        },
                        # REMOVE pending_season promotes a pending (not-yet-started)
                        # renewal lookup to a real season once it starts; a no-op on the
                        # common refresh where the marker was never set (backend/league-onboarding / backend/scheduled-sleeper-auto-refresh).
                        "UpdateExpression": "ADD seasons :s SET platform = :p, league_id = :l REMOVE pending_season",
                        "ExpressionAttributeValues": {
                            ":s": {"SS": seasons},
                            ":p": {"S": platform},
                            ":l": {"S": league_id},
                        },
                    }
                }

            # Job status now lives in the JOB_STATUS item (keyed by correlation_id);
            # the refresh's only DynamoDB write here is the LEAGUE_LOOKUP update.
            transact_items = [league_lookup_operation]
        else:
            metadata_item = {
                "PK": {"S": f"LEAGUE#{canonical_league_id}"},
                "SK": {"S": "METADATA"},
                "platform": {"S": platform},
                "onboarded_at": {"S": now_iso},
            }
            # Record the onboarding owner as the authorization anchor and seed the
            # read-membership set with them (backend/league-authorization). Skipped for
            # system-initiated onboards (no owner), keeping ``members`` absent.
            if owner_user_id:
                metadata_item["owner_user_id"] = {"S": owner_user_id}
                metadata_item["members"] = {"SS": [owner_user_id]}
            transact_items = [
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": metadata_item,
                    }
                },
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "PK": {"S": f"LEAGUE#{league_id}#PLATFORM#{platform}"},
                            "SK": {"S": "LEAGUE_LOOKUP"},
                            "canonical_league_id": {"S": canonical_league_id},
                            "seasons": {"SS": seasons},
                            "platform": {"S": platform},
                            "league_id": {"S": league_id},
                        },
                    }
                },
            ]

        logger.info(
            "Writing onboarding status to DynamoDB: canonical_league_id=%s request_type=%s is_new_season_refresh=%s",
            canonical_league_id,
            request_type,
            is_new_season_refresh,
        )
        _dynamodb.transact_write_items(TransactItems=transact_items)
    except KeyError:
        logger.error("Environment variable 'DYNAMODB_TABLE_NAME' not set!")
        raise
    except botocore.exceptions.ClientError as e:
        logger.error(
            "Error occurred while writing onboarding job status to DynamoDB: %s", e
        )
        raise
