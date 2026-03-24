import json
from typing import Any

import boto3


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
    s3 = boto3.client("s3")
    json_data = json.dumps(results)
    s3.put_object(
        Bucket=bucket_name, Key=key_name, Body=json_data, ContentType="application/json"
    )
