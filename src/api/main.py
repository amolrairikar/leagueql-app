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


def delete_prefixed_items(pk_value: str, sk_prefix: str) -> None:
    """
    Queries and deletes all items sharing a PK and a specific SK prefix.

    Args:
        pk_value: The value of the PK to match.
        sk_prefix: The prefix of the SK to match for deletion.
    """
    query_kwargs: dict = {
        "KeyConditionExpression": Key("PK").eq(pk_value)
        & Key("SK").begins_with(sk_prefix),
        "ProjectionExpression": "PK, SK",
    }
    total_deleted = 0
    try:
        with table.batch_writer() as writer:
            while True:
                response = table.query(**query_kwargs)
                items = response.get("Items", [])
                for item in items:
                    writer.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                total_deleted += len(items)
                last_key = response.get("LastEvaluatedKey")
                if not last_key:
                    break
                query_kwargs["ExclusiveStartKey"] = last_key
    except botocore.exceptions.ClientError as e:
        logger.error(
            "Boto error occurred while deleting items with prefix %s: %s", sk_prefix, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete league data",
        )
    logger.info("Deleted %d items with prefix %s", total_deleted, sk_prefix)


def update_league_count(delta: int) -> None:
    table.update_item(
        Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
        UpdateExpression="ADD league_count :delta",
        ExpressionAttributeValues={":delta": Decimal(str(delta))},
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
        league_pk = f"LEAGUE#{canonical_league_id}"
        table.delete_item(
            Key={"PK": league_pk, "SK": "METADATA"},
        )

        lookup_kwargs: dict = {
            "IndexName": "GSI1",
            "KeyConditionExpression": Key("canonical_league_id").eq(
                canonical_league_id
            ),
        }
        with table.batch_writer() as writer:
            while True:
                lookup_response = table.query(**lookup_kwargs)
                for item in lookup_response.get("Items", []):
                    writer.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                last_key = lookup_response.get("LastEvaluatedKey")
                if not last_key:
                    break
                lookup_kwargs["ExclusiveStartKey"] = last_key

        prefixes_to_clear = [
            "MATCHUPS#",
            "TEAMS#",
            "STANDINGS#",
            "WEEKLY_STANDINGS#",
            "PLAYOFF_BRACKET#",
            "DRAFT#",
        ]
        for prefix in prefixes_to_clear:
            delete_prefixed_items(pk_value=league_pk, sk_prefix=prefix)

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
