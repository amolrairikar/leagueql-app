import json
import logging
import os
import time
from enum import Enum
from typing import Annotated, Any, Optional

import boto3
import botocore.exceptions
from fastapi import FastAPI, HTTPException, Path, Response, status, Query
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel

ORIGINS = [
    "http://localhost:5173",  # LOCAL/DEV
]


class APIResponse(BaseModel):
    detail: str
    data: Optional[Any] = None


class OnboardingPayload(BaseModel):
    leagueId: str
    platform: str
    season: Optional[str] = None
    s2: Optional[str] = None
    swid: Optional[str] = None


class Platform(str, Enum):
    SLEEPER = "SLEEPER"
    ESPN = "ESPN"

    @classmethod
    def _missing_(cls, value: object):
        """Standard-compliant override for case-insensitive lookup."""
        if isinstance(value, str):
            normalized_value = value.upper()
            for member in cls:
                if member.value == normalized_value:
                    return member
        return None


class RequestType(str, Enum):
    ONBOARD = "ONBOARD"
    REFRESH = "REFRESH"

    @classmethod
    def _missing_(cls, value: object):
        """Standard-compliant override for case-insensitive lookup."""
        if isinstance(value, str):
            normalized_value = value.upper()
            for member in cls:
                if member.value == normalized_value:
                    return member
        return None


class JsonFormatter(logging.Formatter):
    """Class to format logs in JSON format."""

    def format(self, record) -> str:
        """
        Format the log record as a JSON object.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: JSON formatted log string.
        """
        log_object = {
            "timestamp": int(time.time() * 1000),
            "level": record.levelname,
            "message": record.getMessage(),
            "function": record.funcName,
        }
        return json.dumps(log_object)


def setup_logger() -> logging.Logger:
    """
    Set up the logger with JSON formatted log entries.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    return logger


logger = setup_logger()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: look into adding a custom config for retries for resource
dynamodb_resource = boto3.resource("dynamodb")
table = dynamodb_resource.Table(os.environ["DYNAMODB_TABLE_NAME"])
dynamodb_client = boto3.client("dynamodb")

lambda_client = boto3.client("lambda")

s3_client = boto3.client("s3")
S3_BUCKET = os.environ["S3_BUCKET_NAME"]


def lookup_league(league_id: str, platform: Platform) -> str:
    """
    Utility function to lookup a given league.

    Args:
        league_id: The ID for the league.
        platform: The platform the league is on (e.g., ESPN, SLEEPER).

    Returns:
        The canonical league ID associated with that league.
    """
    pk = f"LEAGUE#{league_id}#PLATFORM#{platform.value}"
    sk = "LEAGUE_LOOKUP"
    try:
        response = table.get_item(Key={"PK": pk, "SK": sk})
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    item = response.get("Item")
    if not item:
        logger.warning("League %s not found for %s platform", league_id, platform.value)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League {league_id} not found for {platform.value} platform",
        )

    if not item.get("canonical_league_id"):
        logger.error(
            "canonical_league_id not found in item for league %s on platform %s",
            league_id,
            platform.value,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"canonical_league_id not created for league {league_id} on {platform.value} platform",
        )

    return item["canonical_league_id"]


@app.get("/", status_code=status.HTTP_200_OK)
def root() -> APIResponse:
    """Makes health check to API root URL."""
    return APIResponse(detail="Healthy!")


@app.get("/leagues/{leagueId}", status_code=status.HTTP_200_OK)
def get_league(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
) -> APIResponse:
    """Gets league by league ID and platform."""
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    logger.info(
        "Canonical league for league ID %s and platform %s: %s",
        leagueId,
        platform,
        canonical_league_id,
    )
    return APIResponse(
        detail="Found league",
        data={"canonical_league_id": canonical_league_id},
    )


@app.post("/leagues", status_code=status.HTTP_201_CREATED)
def onboard_league(
    payload: OnboardingPayload,
    response: Response,
    requestType: Annotated[
        RequestType, Query(description="The type of request: ONBOARD or REFRESH")
    ] = RequestType.ONBOARD,
) -> APIResponse:
    """Onboard a league to the application."""
    platform = Platform(payload.platform)
    canonical_league_id = None

    try:
        canonical_league_id = lookup_league(
            league_id=payload.leagueId, platform=platform
        )
    except HTTPException as e:
        if e.status_code != status.HTTP_404_NOT_FOUND:
            raise

    if requestType == RequestType.ONBOARD and canonical_league_id:
        logger.info(
            "League %s already onboarded, returning existing data", payload.leagueId
        )
        response.status_code = status.HTTP_200_OK
        return APIResponse(
            detail="League already onboarded",
            data={"canonical_league_id": canonical_league_id},
        )

    if requestType == RequestType.REFRESH and not canonical_league_id:
        if platform != Platform.SLEEPER:
            logger.warning(
                "League %s not found for %s platform, cannot refresh non-existent league",
                payload.leagueId,
                platform.value,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League {payload.leagueId} not found for {platform.value} platform, unable to refresh league",
            )
        logger.info(
            "Sleeper league %s not found in LEAGUE_LOOKUP; onboarder will resolve via previous_league_id chain",
            payload.leagueId,
        )

    log_msg = (
        "Refreshing existing league" if canonical_league_id else "New league detected"
    )
    logger.info(f"{log_msg}, proceeding with Lambda trigger...")

    try:
        lambda_client.invoke(
            FunctionName=os.environ["ONBOARDER_LAMBDA_NAME"],
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "body": payload.model_dump(),
                    "requestType": requestType.value,
                    "canonicalLeagueId": canonical_league_id,
                }
            ),
        )

        detail_msg = (
            "Successfully triggered refresh"
            if canonical_league_id
            else "Successfully triggered onboarding"
        )
        return APIResponse(detail=detail_msg)

    except botocore.exceptions.ClientError as e:
        logger.error("Failed to trigger onboarding/refresh: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger processing",
        )


@app.delete("/leagues/{leagueId}", status_code=status.HTTP_200_OK)
def delete_league(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
) -> APIResponse:
    """Deletes an onboarded league."""
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    logger.info(
        "Proceeding with delete for canonical_league_id: %s", canonical_league_id
    )
    try:
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    "Delete": {
                        "TableName": os.environ["DYNAMODB_TABLE_NAME"],
                        "Key": {
                            "PK": {"S": f"LEAGUE#{canonical_league_id}"},
                            "SK": {"S": "METADATA"},
                        },
                    }
                },
                {
                    "Delete": {
                        "TableName": os.environ["DYNAMODB_TABLE_NAME"],
                        "Key": {
                            "PK": {"S": f"LEAGUE#{canonical_league_id}"},
                            "SK": {"S": "TEAMS"},
                        },
                    }
                },
                {
                    "Delete": {
                        "TableName": os.environ["DYNAMODB_TABLE_NAME"],
                        "Key": {
                            "PK": {"S": f"LEAGUE#{leagueId}#PLATFORM#{platform.value}"},
                            "SK": {"S": "LEAGUE_LOOKUP"},
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": os.environ["DYNAMODB_TABLE_NAME"],
                        "Key": {"PK": {"S": "APP#STATS"}, "SK": {"S": "LEAGUE_COUNT"}},
                        "UpdateExpression": "SET #c = #c - :val",
                        "ConditionExpression": "attribute_exists(PK) AND #c > :zero",
                        "ExpressionAttributeNames": {"#c": "count"},
                        "ExpressionAttributeValues": {
                            ":val": {"N": "1"},
                            ":zero": {"N": "0"},
                        },
                    }
                },
            ]
        )
        logger.info("Deleted league items from DynamoDB")

        # After DB delete, delete raw API data files from S3
        s3_prefix = f"raw-api-data/{canonical_league_id}/"
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=s3_prefix)
        if "Contents" in response:
            delete_keys = [{"Key": obj["Key"]} for obj in response["Contents"]]

            # S3 delete_objects can handle up to 1,000 keys per request
            s3_client.delete_objects(
                Bucket=S3_BUCKET,
                Delete={
                    "Objects": delete_keys,
                    "Quiet": True,  # Returns only errors in the response
                },
            )

        logger.info("Deleted raw API data for league from S3")

        return APIResponse(
            detail="Successfully deleted league",
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Error occurred while deleting league: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


handler = Mangum(app)
