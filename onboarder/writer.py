import json
import os
import time
import uuid
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


def write_onboarding_job_id_to_dynamodb() -> str:
    """
    Writes the onboarding job ID and status to DynamoDB for client to poll to determine onboarding status.

    Returns:
        The UUID corresponding to the current onboarding job run
    """
    try:
        dynamodb = boto3.client("dynamodb")
        job_id = str(uuid.uuid4())
        dynamodb.put_item(
            TableName=os.environ["DYNAMODB_TABLE_NAME"],
            Item={
                "PK": {"S": f"JOB#{job_id}"},
                "SK": {"S": "ONBOARDING_STATUS"},
                "status": {"S": "onboarding"},
                "expiration_time": {"N": str(int(time.time() + 86400))},
            },
        )
        return job_id
    except KeyError as e:
        logger.error("Environment variable 'DYNAMODB_TABLE_NAME' not set!")
        raise e
    except botocore.exceptions.ClientError as e:
        logger.error(
            "Error occurred while writing onboarding job status to DynamoDB: %s", e
        )
        raise e
