import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Optional

import boto3
import botocore.config
import botocore.exceptions
import requests as http_requests
from boto3.dynamodb.conditions import Key
from fastapi import FastAPI, HTTPException, Path, Response, status, Query
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel, Field

ORIGINS = [
    "http://localhost:5173",  # LOCAL/DEV
    "https://leagueql.com",  # PROD
]

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class APIResponse(BaseModel):
    detail: str
    data: Optional[Any] = None


class QueryResponse(BaseModel):
    data: list[Any]


def convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


class OnboardingPayload(BaseModel):
    leagueId: str = Field(max_length=100)
    platform: str = Field(max_length=100)
    season: Optional[str] = Field(default=None, max_length=100)
    s2: Optional[str] = Field(default=None)
    swid: Optional[str] = Field(default=None, max_length=100)


class CaseInsensitiveEnum(str, Enum):
    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            normalized_value = value.upper()
            for member in cls:
                if member.value == normalized_value:
                    return member
        return None


class Platform(CaseInsensitiveEnum):
    SLEEPER = "SLEEPER"
    ESPN = "ESPN"


class RequestType(CaseInsensitiveEnum):
    ONBOARD = "ONBOARD"
    REFRESH = "REFRESH"
    MIGRATE = "MIGRATE"


class SubscriptionStatus(CaseInsensitiveEnum):
    FREE = "FREE"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"


DEFAULT_SUBSCRIPTION_STATUS = SubscriptionStatus.ACTIVE


class QueryType(CaseInsensitiveEnum):
    TEAMS = "TEAMS"
    MATCHUPS = "MATCHUPS"
    SEASON_STANDINGS = "SEASON_STANDINGS"
    WEEKLY_STANDINGS = "WEEKLY_STANDINGS"
    PLAYOFF_BRACKET = "PLAYOFF_BRACKET"
    DRAFT = "DRAFT"
    PLATFORM_MIGRATION = "PLATFORM_MIGRATION"


QUERY_TYPE_TO_SK_BASE = {
    QueryType.TEAMS: "TEAMS",
    QueryType.MATCHUPS: "MATCHUPS",
    QueryType.SEASON_STANDINGS: "STANDINGS",
    QueryType.WEEKLY_STANDINGS: "WEEKLY_STANDINGS",
    QueryType.PLAYOFF_BRACKET: "PLAYOFF_BRACKET",
    QueryType.DRAFT: "DRAFT",
    QueryType.PLATFORM_MIGRATION: "PLATFORM_MIGRATION",
}


class EspnMembersPayload(BaseModel):
    swid: str
    s2: str


class MigratePayload(BaseModel):
    newPlatformLeagueId: str = Field(max_length=100)
    newPlatform: Platform
    season: Optional[str] = Field(default=None, max_length=10)
    s2: Optional[str] = Field(default=None)
    swid: Optional[str] = Field(default=None, max_length=100)
    managerMapping: list[dict] = Field(default_factory=list)


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
            "correlation_id": correlation_id_var.get(),
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
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

REFRESH_COOLDOWN_MINUTES = 30

DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]

_retry_config = botocore.config.Config(retries={"mode": "standard"})
dynamodb_resource = boto3.resource("dynamodb", config=_retry_config)
table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)

lambda_client = boto3.client("lambda", config=_retry_config)

s3_client = boto3.client("s3", config=_retry_config)
S3_BUCKET = os.environ["S3_BUCKET_NAME"]

_sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
_sns_client = boto3.client("sns", config=_retry_config) if _sns_topic_arn else None


def publish_failure(error_message: str) -> None:
    if not _sns_client:
        return
    try:
        _sns_client.publish(
            TopicArn=_sns_topic_arn,
            Subject="LeagueQL API Failure",
            Message=f"Correlation ID: {correlation_id_var.get()}\nError: {error_message}",
        )
    except Exception:
        logger.warning("Failed to publish SNS failure notification", exc_info=True)


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
            detail="Failed to look up league",
        )

    item = response.get("Item")
    if not item:
        logger.warning("League %s not found for %s platform", league_id, platform.value)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found",
        )

    if not item.get("canonical_league_id"):
        logger.error(
            "canonical_league_id not found in item for league %s on platform %s",
            league_id,
            platform.value,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return item["canonical_league_id"]


def get_league_metadata(canonical_league_id: str) -> dict:
    """
    Utility function to get league metadata for a given canonical league ID.

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A dictionary containing the league metadata.
    """
    pk = f"LEAGUE#{canonical_league_id}"
    sk = "METADATA"
    try:
        response = table.get_item(Key={"PK": pk, "SK": sk})
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )

    item = response.get("Item")
    if not item:
        logger.warning("League with canonical ID %s not found", canonical_league_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return item


def get_league_seasons(canonical_league_id: str) -> list[str]:
    """
    Uses GSI1 to find all seasons a league has been onboarded for.

    Queries all LEAGUE_LOOKUP items that share the given canonical_league_id
    (there may be multiple for Sleeper leagues) and merges their season sets.

    Args:
        canonical_league_id: The canonical league ID to look up.

    Returns:
        A sorted list of unique season strings (e.g. ["2022", "2023", "2025"]).
    """
    try:
        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("canonical_league_id").eq(canonical_league_id),
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league seasons",
        )

    items = response.get("Items", [])
    if not items:
        logger.warning(
            "No LEAGUE_LOOKUP items found for canonical_league_id %s",
            canonical_league_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    seasons: set[str] = set()
    for item in items:
        seasons.update(item.get("seasons", set()))

    return sorted(seasons)


def _query_all_keys(query_kwargs: dict) -> list[dict]:
    """
    Run a paginated query, returning every matched item's {PK, SK} key.

    Args:
        query_kwargs: Keyword arguments passed to table.query (must project PK/SK).

    Returns:
        A list of {"PK", "SK"} key dicts across all result pages.
    """
    keys: list[dict] = []
    kwargs = dict(query_kwargs)
    while True:
        response = table.query(**kwargs)
        for item in response.get("Items", []):
            keys.append({"PK": item["PK"], "SK": item["SK"]})
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return keys
        kwargs["ExclusiveStartKey"] = last_key


def collect_league_keys(canonical_league_id: str) -> list[dict]:
    """
    Collect the keys of every DynamoDB item belonging to a league.

    This covers two key spaces:
      * everything under the canonical PK (METADATA and all precomputed views,
        including any future SK types) read with strong consistency, and
      * the LEAGUE_LOOKUP items, which live under their own per-platform PKs and
        are located via GSI1 (eventually consistent).

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A list of {"PK", "SK"} key dicts for every item owned by the league.
    """
    keys = _query_all_keys(
        {
            "KeyConditionExpression": Key("PK").eq(f"LEAGUE#{canonical_league_id}"),
            "ProjectionExpression": "PK, SK",
            "ConsistentRead": True,
        }
    )
    keys += _query_all_keys(
        {
            "IndexName": "GSI1",
            "KeyConditionExpression": Key("canonical_league_id").eq(
                canonical_league_id
            ),
            "ProjectionExpression": "PK, SK",
        }
    )
    return keys


def delete_all_league_items(canonical_league_id: str, max_attempts: int = 4) -> None:
    """
    Delete every DynamoDB item for a league, retrying until none remain.

    Rather than deleting a hardcoded set of SK prefixes, this discovers the
    league's actual items on each pass and deletes them, then re-verifies. This
    catches orphaned items (e.g. PLATFORM_MIGRATION#) regardless of SK type and
    tolerates GSI1 eventual-consistency lag on LEAGUE_LOOKUP items.

    Args:
        canonical_league_id: The canonical league ID.
        max_attempts: Number of delete+verify passes before giving up.

    Raises:
        HTTPException: 500 if items still remain after max_attempts.
    """
    for attempt in range(1, max_attempts + 1):
        keys = collect_league_keys(canonical_league_id)
        if not keys:
            return
        logger.info(
            "Delete attempt %d/%d: removing %d items for %s",
            attempt,
            max_attempts,
            len(keys),
            canonical_league_id,
        )
        with table.batch_writer() as writer:
            for key in keys:
                writer.delete_item(Key=key)
        time.sleep(0.5 * attempt)  # let GSI1 catch up before re-verifying

    remaining = collect_league_keys(canonical_league_id)
    if remaining:
        remaining_sks = [key["SK"] for key in remaining]
        logger.error(
            "Orphaned items remain for %s after %d attempts: %s",
            canonical_league_id,
            max_attempts,
            remaining_sks,
        )
        publish_failure(
            f"Orphaned items remain for league {canonical_league_id} after "
            f"{max_attempts} delete attempts: {remaining_sks}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fully delete league data",
        )


def update_league_count(delta: int) -> None:
    table.update_item(
        Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
        UpdateExpression="ADD league_count :delta",
        ExpressionAttributeValues={":delta": Decimal(str(delta))},
    )


def update_subscription_status(
    canonical_league_id: str, new_status: SubscriptionStatus
) -> None:
    """
    Sets the subscription state on a league's METADATA item.

    Args:
        canonical_league_id: The canonical league ID.
        new_status: The subscription state to set.
    """
    # TODO(billing): no public/authenticated route exposes this yet. For now
    # subscription state is changed manually (script/console). A guarded endpoint
    # or payment-provider webhook backed by this helper is the enforcement-phase
    # follow-up.
    table.update_item(
        Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
        UpdateExpression="SET subscription_status = :s",
        ConditionExpression="attribute_exists(PK)",
        ExpressionAttributeValues={":s": new_status.value},
    )


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
    response: Response,
) -> APIResponse:
    """Gets league by league ID and platform."""
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    logger.info(
        "Canonical league for league ID %s and platform %s: %s",
        leagueId,
        platform,
        canonical_league_id,
    )
    seasons = get_league_seasons(canonical_league_id=canonical_league_id)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    response.headers["Cache-Control"] = "no-store"
    return APIResponse(
        detail="Found league",
        data={
            "seasons": seasons,
            "league_name": metadata.get("league_name"),
            "subscription_status": metadata.get(
                "subscription_status", DEFAULT_SUBSCRIPTION_STATUS.value
            ),
        },
    )


@app.get("/leagues/{leagueId}/refresh_status", status_code=status.HTTP_200_OK)
def get_refresh_status(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    refreshOperation: Annotated[
        RequestType,
        Query(
            description="The type of refresh ('ONBOARD' or 'REFRESH') to check the status of"
        ),
    ],
    response: Response,
) -> APIResponse:
    """Gets the refresh status for a given league."""
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    league_metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    if refreshOperation in (RequestType.ONBOARD, RequestType.MIGRATE):
        refresh_status = league_metadata.get("onboarding_status", "FAILED")
    else:
        refresh_status = league_metadata.get("refresh_status", "FAILED")

    response.headers["Cache-Control"] = "no-store"
    return APIResponse(
        detail="Found refresh status",
        data={
            "refresh_operation": refreshOperation.value,
            "refresh_status": refresh_status,
        },
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
    correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
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
        return APIResponse(detail="League already onboarded")

    if requestType == RequestType.REFRESH and not canonical_league_id:
        if platform != Platform.SLEEPER:
            logger.warning(
                "League %s not found for %s platform, cannot refresh non-existent league",
                payload.leagueId,
                platform.value,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="League not found",
            )
        logger.info(
            "Sleeper league %s not found in LEAGUE_LOOKUP; onboarder will resolve via previous_league_id chain",
            payload.leagueId,
        )

    if requestType == RequestType.REFRESH and canonical_league_id:
        league_metadata = get_league_metadata(canonical_league_id)
        if (
            league_metadata.get("refresh_status") == "IN_PROGRESS"
            or league_metadata.get("onboarding_status") == "IN_PROGRESS"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A refresh is already in progress for this league",
            )
        last_refresh_at = league_metadata.get("last_refresh_at")
        if last_refresh_at:
            last_refresh_dt = datetime.fromisoformat(last_refresh_at)
            if datetime.now(timezone.utc) - last_refresh_dt < timedelta(
                minutes=REFRESH_COOLDOWN_MINUTES
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"League was refreshed recently. Please wait {REFRESH_COOLDOWN_MINUTES} minutes before refreshing again.",
                )

    log_msg = (
        "Refreshing existing league" if canonical_league_id else "New league detected"
    )
    logger.info("%s, proceeding with Lambda trigger...", log_msg)

    try:
        lambda_client.invoke(
            FunctionName=os.environ["ONBOARDER_LAMBDA_NAME"],
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "body": payload.model_dump(),
                    "requestType": requestType.value,
                    "canonicalLeagueId": canonical_league_id,
                    "correlation_id": correlation_id,
                }
            ),
        )

        detail_msg = (
            "Successfully triggered refresh"
            if canonical_league_id
            else "Successfully triggered onboarding"
        )
        return APIResponse(detail=detail_msg, data={"correlation_id": correlation_id})

    except botocore.exceptions.ClientError as e:
        logger.error("Failed to trigger onboarding/refresh: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger processing",
        )


@app.post("/leagues/{leagueId}/espn_members", status_code=status.HTTP_200_OK)
def get_espn_members(
    leagueId: Annotated[
        str, Path(description="The ID of the current league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The current platform")],
    espnLeagueId: Annotated[
        str, Query(description="The ESPN league ID to fetch members from")
    ],
    season: Annotated[str, Query(description="The ESPN season year")],
    payload: EspnMembersPayload,
) -> APIResponse:
    """Proxy ESPN Fantasy API to fetch league members server-side (avoids browser CORS)."""
    lookup_league(league_id=leagueId, platform=platform)

    espn_url = (
        f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
        f"/seasons/{season}/segments/0/leagues/{espnLeagueId}?view=mTeam"
    )
    try:
        espn_response = http_requests.get(
            espn_url,
            cookies={"SWID": payload.swid, "espn_s2": payload.s2},
            timeout=10,
        )
        espn_response.raise_for_status()
    except http_requests.exceptions.HTTPError as e:
        logger.error("ESPN API error fetching members: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch ESPN league members",
        )
    except http_requests.exceptions.RequestException as e:
        logger.error("Request error fetching ESPN members: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach ESPN API",
        )

    try:
        espn_data = espn_response.json()
        members = [
            {"owner_id": m["id"], "display_name": m.get("displayName", m["id"])}
            for m in espn_data.get("members", [])
        ]
    except (KeyError, ValueError) as e:
        logger.error("Failed to parse ESPN members response: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse ESPN API response",
        )

    return APIResponse(detail="Found ESPN members", data=members)


@app.post("/leagues/{leagueId}/migrate", status_code=status.HTTP_202_ACCEPTED)
def migrate_league(
    leagueId: Annotated[
        str, Path(description="The ID of the current platform league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The current platform")],
    payload: MigratePayload,
    response: Response,
) -> APIResponse:
    """Migrate a league from one platform to another."""
    correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)

    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    logger.info(
        "Migration requested: canonical_league_id=%s from=%s to=%s",
        canonical_league_id,
        platform.value,
        payload.newPlatform.value,
    )

    league_metadata = get_league_metadata(canonical_league_id)
    if (
        league_metadata.get("onboarding_status") == "IN_PROGRESS"
        or league_metadata.get("refresh_status") == "IN_PROGRESS"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An operation is already in progress for this league",
        )

    try:
        lookup_league(
            league_id=payload.newPlatformLeagueId, platform=payload.newPlatform
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="New platform league is already onboarded",
        )
    except HTTPException as e:
        if e.status_code != status.HTTP_404_NOT_FOUND:
            raise

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        table.put_item(
            Item={
                "PK": f"LEAGUE#{payload.newPlatformLeagueId}#PLATFORM#{payload.newPlatform.value}",
                "SK": "LEAGUE_LOOKUP",
                "canonical_league_id": canonical_league_id,
                "platform": payload.newPlatform.value,
                "league_id": payload.newPlatformLeagueId,
            }
        )

        table.put_item(
            Item={
                "PK": f"LEAGUE#{canonical_league_id}",
                "SK": f"PLATFORM_MIGRATION#{platform.value}#{payload.newPlatform.value}",
                "data": payload.managerMapping,
            }
        )

        table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression=(
                "SET active_platform = :ap, migrated_from = :mf, "
                "migrated_at = :ma, onboarding_status = :os, #p = :ap"
            ),
            ExpressionAttributeNames={"#p": "platform"},
            ExpressionAttributeValues={
                ":ap": payload.newPlatform.value,
                ":mf": platform.value,
                ":ma": now_iso,
                ":os": "IN_PROGRESS",
            },
        )
    except botocore.exceptions.ClientError as e:
        logger.error("DynamoDB error during migration setup: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set up migration",
        )

    try:
        lambda_client.invoke(
            FunctionName=os.environ["ONBOARDER_LAMBDA_NAME"],
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "body": {
                        "leagueId": payload.newPlatformLeagueId,
                        "platform": payload.newPlatform.value,
                        "season": payload.season,
                        "s2": payload.s2,
                        "swid": payload.swid,
                    },
                    "requestType": "MIGRATE",
                    "canonicalLeagueId": canonical_league_id,
                    "correlation_id": correlation_id,
                }
            ),
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to invoke onboarder Lambda for migration: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger migration",
        )

    response.status_code = status.HTTP_202_ACCEPTED
    return APIResponse(
        detail="Migration started", data={"correlation_id": correlation_id}
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
        delete_all_league_items(canonical_league_id=canonical_league_id)

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

        update_league_count(delta=-1)
        return APIResponse(
            detail="Successfully deleted league",
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Error occurred while deleting league: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete league",
        )


@app.get("/leagues/{leagueId}/query", status_code=status.HTTP_200_OK)
def query_league(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    queryType: Annotated[str, Query(description="The precomputed view to retrieve")],
    response: Response,
) -> QueryResponse:
    """Returns a precomputed data view for the specified league."""
    parts = queryType.split("#", 1)
    base_type_str = parts[0].upper()
    suffix = parts[1] if len(parts) > 1 else None

    try:
        base_type = QueryType(base_type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid queryType. See API documentation for supported values.",
        )

    sk_base = QUERY_TYPE_TO_SK_BASE[base_type]
    sk = f"{sk_base}#{suffix}" if suffix is not None else f"{sk_base}#"

    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    pk = f"LEAGUE#{canonical_league_id}"

    try:
        if sk.endswith("#"):
            items: list[Any] = []
            kwargs: dict[str, Any] = {
                "KeyConditionExpression": Key("PK").eq(pk) & Key("SK").begins_with(sk),
            }
            while True:
                db_response = table.query(**kwargs)
                items.extend(db_response.get("Items", []))
                last_key = db_response.get("LastEvaluatedKey")
                if not last_key:
                    break
                kwargs["ExclusiveStartKey"] = last_key
            if not items:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No data found for the requested query",
                )
            all_data: list[Any] = []
            for item in items:
                all_data.extend(item.get("data", []))
            response.headers["Cache-Control"] = "private, max-age=300"
            return QueryResponse(data=convert_decimals(all_data))
        else:
            db_response = table.get_item(Key={"PK": pk, "SK": sk}, ConsistentRead=True)
            item = db_response.get("Item")
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No data found for the requested query",
                )
            response.headers["Cache-Control"] = "private, max-age=300"
            return QueryResponse(data=convert_decimals(item.get("data", [])))
    except HTTPException:
        raise
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )


handler = Mangum(app)
