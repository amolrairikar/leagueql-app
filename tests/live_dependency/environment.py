import logging

import boto3
import botocore.exceptions
from behave.model import Scenario
from behave.runner import Context


logger = logging.getLogger(__name__)


def clear_dynamodb_table(table_name: str, region: str = "us-east-1") -> None:
    """
    Clears all items from a DynamoDB table by scanning and batch-deleting everything.

    Args:
        table_name: Name of the DynamoDB table to clear.
        region: AWS region where the table lives (default: us-east-1).

    Raises:
        ClientError: If DynamoDB returns an unrecoverable error (e.g. table does
            not exist, insufficient permissions).
    """
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    try:
        key_names = {key["AttributeName"] for key in table.key_schema}
    except botocore.exceptions.ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ResourceNotFoundException":
            raise botocore.exceptions.ClientError(e.response, "key_schema") from e
        logger.error("Failed to describe table '%s': %s", table_name, e)
        raise

    deleted_count = 0
    scan_kwargs = {}
    while True:
        try:
            response = table.scan(**scan_kwargs)
        except botocore.exceptions.ClientError as e:
            logger.error("Failed to scan table '%s': %s", table_name, e)
            raise

        items = response.get("Items", [])
        if not items:
            break

        try:
            with table.batch_writer() as batch:
                for item in items:
                    key = {k: v for k, v in item.items() if k in key_names}
                    batch.delete_item(Key=key)
            deleted_count += len(items)
        except botocore.exceptions.ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ProvisionedThroughputExceededException":
                logger.warning(
                    "Throughput exceeded while clearing '%s' — consider increasing "
                    "table capacity or adding a retry delay.",
                    table_name,
                )
            logger.error("Failed to delete items from '%s': %s", table_name, e)
            raise

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    print(f"Deleted {deleted_count} item(s) from table '{table_name}'.")


TABLE_NAME = "fantasy-football-recap-table-dev"
REGION = "us-east-1"


def before_all(context: Context):
    """Wipe the table clean before the test suite starts."""
    clear_dynamodb_table(TABLE_NAME, REGION)


def after_all(context: Context):
    """Wipe the table clean after the entire test suite finishes."""
    clear_dynamodb_table(TABLE_NAME, REGION)


def after_scenario(context: Context, scenario: Scenario):
    """Wipe the table after any scenario tagged with @writes_data."""
    if "writes_data" in scenario.tags:
        clear_dynamodb_table(TABLE_NAME, REGION)
