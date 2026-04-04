import datetime
import json
import os
from typing import Any

import boto3
import botocore.exceptions

from utils import logger


def upload_results_to_s3(
    results: list[dict[str, Any]], bucket_name: str, prefix: str, platform: str
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
        s3 = boto3.client("s3")

        seasons_data: dict[str, list[dict[str, Any]]] = {}
        for item in results:
            season = str(item["season"])
            seasons_data.setdefault(season, []).append(item)

        for season, season_results in seasons_data.items():
            s3.put_object(
                Bucket=bucket_name,
                Key=f"{prefix}/{season}.json",
                Body=json.dumps(season_results),
                ContentType="application/json",
            )

        manifest_key = f"{prefix}/manifest.json"
        try:
            existing_manifest_obj = s3.get_object(Bucket=bucket_name, Key=manifest_key)
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

        s3.put_object(
            Bucket=bucket_name,
            Key=f"{prefix}/manifest.json",
            Body=json.dumps(full_manifest),
            ContentType="application/json",
        )
        logger.info("Wrote manifest to S3")
    except botocore.exceptions.ClientError as e:
        logger.error("Error occurred while writing raw API JSON to S3: %s", e)
        raise e


def write_onboarding_status_to_dynamodb(
    league_id: str,
    platform: str,
    canonical_league_id: str,
    seasons: list[str],
    request_type: str,
    is_new_season_refresh: bool = False,
):
    """
    Writes the onboarding status to DynamoDB for client to poll to determine onboarding status.

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
        dynamodb = boto3.client("dynamodb")
        table_name = os.environ["DYNAMODB_TABLE_NAME"]
        now_iso = datetime.datetime.now().isoformat()

        if request_type == "REFRESH":
            if is_new_season_refresh:
                league_lookup_operation = {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "PK": {"S": f"LEAGUE#{league_id}#PLATFORM#{platform}"},
                            "SK": {"S": "LEAGUE_LOOKUP"},
                            "canonical_league_id": {"S": canonical_league_id},
                            "seasons": {"SS": seasons},
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
                        "UpdateExpression": "ADD seasons :s",
                        "ExpressionAttributeValues": {
                            ":s": {"SS": seasons},
                        },
                    }
                }

            transact_items = [
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {
                            "PK": {"S": f"LEAGUE#{canonical_league_id}"},
                            "SK": {"S": "METADATA"},
                        },
                        "UpdateExpression": "SET refresh_status = :rs, last_refreshed_date = :rd",
                        "ExpressionAttributeValues": {
                            ":rs": {"S": "refreshing"},
                            ":rd": {"S": now_iso},
                        },
                    }
                },
                league_lookup_operation,
            ]
        else:
            transact_items = [
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": {
                            "PK": {"S": f"LEAGUE#{canonical_league_id}"},
                            "SK": {"S": "METADATA"},
                            "platform": {"S": platform},
                            "onboarded_at": {"S": now_iso},
                            "onboarding_status": {"S": "onboarding"},
                        },
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
                        },
                    }
                },
            ]

        dynamodb.transact_write_items(TransactItems=transact_items)
    except KeyError as e:
        logger.error("Environment variable 'DYNAMODB_TABLE_NAME' not set!")
        raise e
    except botocore.exceptions.ClientError as e:
        logger.error(
            "Error occurred while writing onboarding job status to DynamoDB: %s", e
        )
        raise e
