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


lambda_handler(
    event={
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-east-1",
                "eventTime": "2026-03-30T16:15:25.189Z",
                "eventName": "ObjectCreated:Put",
                "userIdentity": {
                    "principalId": "AWS:AROARMDR23X7KAILQ3J7W:fantasy-football-recap-onboarder-dev-east"
                },
                "requestParameters": {"sourceIPAddress": "54.224.121.146"},
                "responseElements": {
                    "x-amz-request-id": "XZYH971K195XDGJ9",
                    "x-amz-id-2": "oOUSovm4RijFI3dWP43fiobHdUYiXWJ4kgi89GIgZsck8109ko9JxS725zoPLTOO05iLd+JWxtSwZCZvsBNqAknr+rU0nJN9",
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "tf-s3-lambda-20260324182610303900000001",
                    "bucket": {
                        "name": "fantasy-football-recap-dev-bucket-east-094728019454",
                        "ownerIdentity": {"principalId": "AX2LKYNFD4ZF1"},
                        "arn": "arn:aws:s3:::fantasy-football-recap-dev-bucket-east-094728019454",
                    },
                    "object": {
                        "key": "raw-api-data/ESPN/71390fa7-9f05-4205-b05e-8b2fec10ce02/onboard.json",
                        "size": 32680849,
                        "eTag": "626ac4163adb9a39a467da4d7d72de8f",
                        "versionId": ".VwvJHJ843xwpBqD2NpzjwVxoNXBbRx2",
                        "sequencer": "0069CAA19CD3D8B108",
                    },
                },
            }
        ]
    },
    context={},
)
