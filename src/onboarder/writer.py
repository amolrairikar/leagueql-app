import datetime
import json
import os
from typing import Any

import boto3
import botocore.config
import botocore.exceptions

from utils import correlation_id_var, logger

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_s3 = boto3.client("s3", config=_retry_config)
_dynamodb = boto3.client("dynamodb", config=_retry_config)


def upload_results_to_s3(
    results: list[dict[str, Any]],
    bucket_name: str,
    prefix: str,
    platform: str,
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


def write_league_records(
    league_id: str,
    platform: str,
    canonical_league_id: str,
    seasons: list[str],
    request_type: str,
    is_new_season_refresh: bool = False,
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
                        "UpdateExpression": "ADD seasons :s SET platform = :p, league_id = :l",
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
            # ``subscription_end_time`` is intentionally NOT written here. It is set
            # only server-side by the Stripe billing webhook (BE-014 / BE-015), so a
            # freshly onboarded, unsubscribed league reads as expired until checkout
            # completes. (Removes the BE-001 interim, client-spoofable input.)
            metadata_item = {
                "PK": {"S": f"LEAGUE#{canonical_league_id}"},
                "SK": {"S": "METADATA"},
                "platform": {"S": platform},
                "onboarded_at": {"S": now_iso},
            }
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
