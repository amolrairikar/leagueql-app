import json
import os
from decimal import Decimal
from typing import Any

import boto3


class DynamoWriter:
    """
    Class for writing transformed league data to DynamoDB.

    Attributes:
        league_id: The ID of the league being onboarded.
        platform: The platform the league is on (e.g., ESPN, SLEEPER)

    Methods:
        __init__(league_id, platform): Constructor.
        write_all(views): Writes each view to DynamoDB using the sort key and corresponding data from the view mapping.
        _serialize(data): Serializes DynamoDB records to convert floats to Decimal.
    """

    def __init__(self, league_id: str, platform: str):
        """Constructor."""
        self.league_id = league_id
        self.platform = platform
        self.table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE_NAME"])
        self.client = boto3.client("dynamodb")

    def write_all(self, views: dict[str, Any]) -> None:
        """
        Writes each view to DynamoDB using the sort key and corresponding data from the view mapping.

        Args:
            views: Mapping containing DynamoDB sort key and the corresponding data.
        """
        with self.table.batch_writer() as batch:
            for sort_key, data in views.items():
                batch.put_item(
                    Item={
                        "PK": f"LEAGUE#{self.league_id}",
                        "SK": sort_key,
                        "data": self._serialize(data),
                    }
                )

        self.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": self.table.name,
                        "Key": {
                            "PK": {"S": f"LEAGUE#{self.league_id}"},
                            "SK": {"S": "METADATA"},
                        },
                        "UpdateExpression": "SET onboarding_status = :val",
                        "ExpressionAttributeValues": {":val": {"S": "completed"}},
                    }
                },
                {
                    "Update": {
                        "TableName": self.table.name,
                        "Key": {"PK": {"S": "APP#STATS"}, "SK": {"S": "LEAGUE_COUNT"}},
                        "UpdateExpression": "ADD #count :inc",
                        "ExpressionAttributeNames": {"#count": "count"},
                        "ExpressionAttributeValues": {":inc": {"N": "1"}},
                    }
                },
            ]
        )

    def _serialize(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Serializes DynamoDB records to convert floats to Decimal.

        Args:
            data: The data to serialize.

        Returns:
            The updated data with floats converted to Decimal.
        """
        return json.loads(json.dumps(data), parse_float=Decimal)
