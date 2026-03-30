import datetime
import json
import os
from typing import Any

import boto3
import botocore.exceptions

from utils import logger


def upload_results_to_s3(
    results: list[dict[str, Any]], bucket_name: str, key_name: str
) -> None:
    """
    Uploads raw API data to S3.

    Args:
        results: List containing raw API results.
        bucket_name: Name of the S3 bucket to upload data to.
        key_name: Full key path within the S3 bucket to upload data to.
    """
    try:
        s3 = boto3.client("s3")
        json_data = json.dumps(results)
        s3.put_object(
            Bucket=bucket_name,
            Key=key_name,
            Body=json_data,
            ContentType="application/json",
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Error occurred while writing raw API JSON to S3: %s", e)
        raise e


def write_onboarding_status_to_dynamodb(
    league_id: str,
    platform: str,
    canonical_league_id: str,
    seasons: list[str],
    request_type: str,
):
    """
    Writes the onboarding status to DynamoDB for client to poll to determine onboarding status.

    Args:
        league_id: The ID for the league on its platform.
        platform: The platform (e.g., ESPN, SLEEPER) that the league is on.
        canonical_league_id: The unique ID for the league.
        seasons: List of strings representing number of seasons league was active for prior to onboarding.
        request_type: The type of onboarding request (e.g., "ONBOARD" or "REFRESH")
    """
    try:
        dynamodb = boto3.client("dynamodb")
        table_name = os.environ["DYNAMODB_TABLE_NAME"]
        now_iso = datetime.datetime.now().isoformat()

        if request_type == "REFRESH":
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
                {
                    "Update": {
                        "TableName": table_name,
                        "Key": {
                            "PK": {"S": f"LEAGUE#{league_id}#PLATFORM#{platform}"},
                            "SK": {"S": "LEAGUE_LOOKUP"},
                        },
                        "UpdateExpression": "SET seasons = :s",
                        "ExpressionAttributeValues": {
                            ":s": {"SS": seasons},
                        },
                    }
                },
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
