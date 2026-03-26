import json
from typing import Any

import boto3
import botocore.exceptions

from dynamo_writer import DynamoWriter
from logging_utils import logger
from transformer import Transformer


def read_s3_object(bucket: str, key: str) -> list[dict[str, Any]]:
    """
    Reads an object from S3 with the given bucket and key.

    Args:
        bucket: The S3 bucket containing the object
        key: The key corresponding to the object location within the bucket.

    Returns:
        The loaded object in JSON format.
    """
    try:
        s3_client = boto3.client("s3")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response["Body"].read().decode("utf-8")
        return json.loads(file_content)
    except botocore.exceptions.ClientError as e:
        logger.error("Error reading raw onboarding data from S3: %s", e)
        raise e


def lambda_handler(event, context) -> dict[str, str | int]:
    """
    Main handler function for processing raw API data fetched by onboarder.

    Args:
        event: The event data that triggered the Lambda function.
        context: The context in which the Lambda function is running.

    Returns:
        dict: A response indicating the success of the operation.
    """
    logger.info("Starting league onboarding process execution.")
    logger.info("Event data: %s", event)
    logger.info("Context data: %s", context)

    put_request_principal = event["Records"][0]["userIdentity"]["principalId"].split(
        ":"
    )[-1]
    logger.info("Put request principal: %s", put_request_principal)
    if put_request_principal == "s3-replication":
        logger.info(
            "Lambda triggered by replication event, no further processing needed."
        )
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "succeeded", "message": "no-op"}),
        }

    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    platform = key.split("/")[1]
    league_id = key.split("/")[2]
    raw_data = read_s3_object(bucket=bucket, key=key)

    transformer = Transformer(platform=platform)
    transformed_data = transformer.transform(raw_data=raw_data)
    dynamo_writer = DynamoWriter(league_id=league_id, platform=platform)
    dynamo_writer.write_all(views=transformed_data)

    return {}
