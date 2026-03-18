import json
import os
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any

import boto3


class DynamoWriter:
    """
    Class for transforming raw API response data into format consumed by application.

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

    def write_all(self, views: dict[str, Any]):
        """
        Writes each view to DynamoDB using the sort key and corresponding data from the view mapping.

        Args:
            views: Mapping containing DynamoDB sort key and the corresponding data.
        """
        with self.table.batch_writer() as batch:
            for sort_key, data in views.items():
                batch.put_item(
                    Item={
                        "PK": f"LEAGUE#{self.league_id}#PLATFORM#{self.platform}",
                        "SK": sort_key,
                        "data": self._serialize(data),
                    }
                )

            # Written last for a league — signals onboarding completed successfully
            batch.put_item(
                Item={
                    "PK": f"LEAGUE#{self.league_id}",
                    "SK": "METADATA",
                    "status": "active",
                    "onboardedAt": datetime.now(timezone.utc).isoformat(),
                }
            )

        self.table.update_item(
            Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
            UpdateExpression="ADD #count :inc",
            ExpressionAttributeNames={"#count": "count"},
            ExpressionAttributeValues={":inc": 1},
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
