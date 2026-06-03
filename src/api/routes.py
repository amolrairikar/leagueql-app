"""FastAPI route handlers for the LeagueQL API.

Routes are registered on an APIRouter that ``main`` includes on the app. AWS
clients (``table``, ``lambda_client``, ``s3_client``) and the ``http_requests``
module are reached through ``main`` at call time so test patches on
``main.table`` etc. take effect here.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import botocore.exceptions
import requests as http_requests
from boto3.dynamodb.conditions import Key
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)

import main
from common.onboarder_invoke import invoke_onboarder
from main import (
    QUERY_TYPE_TO_SK_BASE,
    REFRESH_COOLDOWN_MINUTES,
    S3_BUCKET,
    APIResponse,
    EspnMembersPayload,
    MigratePayload,
    OnboardingPayload,
    Platform,
    QueryResponse,
    QueryType,
    RequestType,
    correlation_id_var,
    logger,
)
from helpers import (
    claim_pending_checkout,
    convert_decimals,
    create_job_status,
    delete_all_league_items,
    get_job_status,
    get_latest_stored_matchup,
    get_league_metadata,
    get_league_seasons,
    get_nfl_state,
    get_or_create_stripe_customer,
    get_stripe_customer_id,
    is_job_in_progress,
    lookup_league,
    require_active_subscription,
    set_active_job,
    update_league_count,
)

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
def root() -> APIResponse:
    """Makes health check to API root URL."""
    return APIResponse(detail="Healthy!")


@router.get("/leagues/{leagueId}", status_code=status.HTTP_200_OK)
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
            "subscription_end_time": metadata.get("subscription_end_time"),
        },
    )


def get_authenticated_user(request: Request) -> str:
    """Return the authenticated Clerk user ID from the API Gateway JWT authorizer.

    The Clerk JWT is validated by the API Gateway authorizer; its verified claims
    are surfaced to the Lambda under the original event, which Mangum exposes at
    ``request.scope["aws.event"]``. Used as a FastAPI dependency for billing
    endpoints that must map the caller to a Stripe customer (BE-015).

    Raises:
        HTTPException: 401 when no authenticated user (``sub`` claim) is present.
    """
    event = request.scope.get("aws.event", {}) or {}
    claims = (
        (event.get("requestContext", {}).get("authorizer", {}) or {})
        .get("jwt", {})
        .get("claims", {})
    )
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return sub


@router.post("/leagues/{leagueId}/checkout-session", status_code=status.HTTP_200_OK)
def create_checkout_session(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Create a Stripe Checkout Session to subscribe a league (BE-015).

    Resolves/creates the caller's Stripe customer, claims a synchronous
    ``pending_checkout`` marker (one winner under concurrency), and opens a
    subscription-mode Checkout Session whose subscription carries the league's
    canonical ID. The trial is included only on the league's first subscription.
    Returns 409 when the league already has a subscription or an unexpired
    in-flight checkout.
    """
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    trial_used = bool(metadata.get("trial_used"))

    customer_id = get_or_create_stripe_customer(clerk_user_id)

    token = uuid.uuid4().hex
    if not claim_pending_checkout(canonical_league_id, token):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A subscription or checkout is already active for this league",
        )

    subscription_data: dict[str, Any] = {
        "metadata": {"canonical_league_id": canonical_league_id},
    }
    if not trial_used:
        subscription_data["trial_period_days"] = main.STRIPE_TRIAL_PERIOD_DAYS

    session = main.stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": main.STRIPE_PRICE_ID, "quantity": 1}],
        subscription_data=subscription_data,
        success_url=main.STRIPE_CHECKOUT_SUCCESS_URL,
        cancel_url=main.STRIPE_CHECKOUT_CANCEL_URL,
        idempotency_key=token,
    )
    logger.info(
        "Created checkout session for league %s (trial=%s)",
        canonical_league_id,
        not trial_used,
    )
    return APIResponse(detail="Checkout session created", data={"url": session["url"]})


@router.post("/billing-portal-session", status_code=status.HTTP_200_OK)
def create_billing_portal_session(
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Create a Stripe Billing Portal session for the caller (BE-015).

    Lets the user manage their card or cancel (cancellation takes effect
    immediately). Returns 404 when the caller has no Stripe customer yet.
    """
    customer_id = get_stripe_customer_id(clerk_user_id)
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing account found",
        )
    session = main.stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=main.STRIPE_BILLING_PORTAL_RETURN_URL,
    )
    return APIResponse(
        detail="Billing portal session created", data={"url": session["url"]}
    )


@router.get("/jobs/{jobId}", status_code=status.HTTP_200_OK)
def get_job(
    jobId: Annotated[
        str,
        Path(
            description="The job (correlation) ID returned when onboarding/refresh was triggered",
            pattern=r"^[0-9a-fA-F-]{36}$",
        ),
    ],
    response: Response,
) -> APIResponse:
    """
    Gets the status of an onboard/refresh/migrate job.

    Returns the job's status plus a user-friendly failure_reason when it failed.
    A missing item (never created, or expired after its 24h TTL) is reported as
    FAILED so the frontend stops polling.
    """
    job = get_job_status(correlation_id=jobId)
    response.headers["Cache-Control"] = "no-store"
    if not job:
        logger.info("No JOB_STATUS found for job %s; reporting FAILED", jobId)
        return APIResponse(detail="Job not found", data={"status": "FAILED"})
    return APIResponse(
        detail="Found job status",
        data={
            "status": job.get("status", "FAILED"),
            "failure_code": job.get("failure_code"),
            "failure_reason": job.get("failure_reason"),
        },
    )


@router.post("/leagues", status_code=status.HTTP_201_CREATED)
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
        require_active_subscription(canonical_league_id, metadata=league_metadata)
        if is_job_in_progress(league_metadata):
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

        nfl_state = get_nfl_state()
        if nfl_state is not None:
            if nfl_state.get("season_type") == "off":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="League is already up to date (NFL offseason).",
                )
            state_season = int(nfl_state["season"])
            state_week = int(nfl_state["week"])
            latest = get_latest_stored_matchup(canonical_league_id)
            if latest is not None and latest >= (state_season, state_week):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="League is already up to date.",
                )

    log_msg = (
        "Refreshing existing league" if canonical_league_id else "New league detected"
    )
    logger.info("%s, proceeding with Lambda trigger...", log_msg)

    create_job_status(
        correlation_id=correlation_id,
        request_type=requestType.value,
        league_id=payload.leagueId,
        platform=platform.value,
        canonical_league_id=canonical_league_id,
    )
    if canonical_league_id:
        set_active_job(canonical_league_id, correlation_id)

    try:
        invoke_onboarder(
            lambda_client=main.lambda_client,
            function_name=os.environ["ONBOARDER_LAMBDA_NAME"],
            body=payload.model_dump(),
            request_type=requestType.value,
            canonical_league_id=canonical_league_id,
            correlation_id=correlation_id,
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


@router.post("/leagues/{leagueId}/espn_members", status_code=status.HTTP_200_OK)
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
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    require_active_subscription(canonical_league_id)

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


@router.post("/leagues/{leagueId}/migrate", status_code=status.HTTP_202_ACCEPTED)
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
    require_active_subscription(canonical_league_id, metadata=league_metadata)
    if is_job_in_progress(league_metadata):
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

    create_job_status(
        correlation_id=correlation_id,
        request_type="MIGRATE",
        league_id=leagueId,
        platform=platform.value,
        canonical_league_id=canonical_league_id,
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        main.table.put_item(
            Item={
                "PK": f"LEAGUE#{payload.newPlatformLeagueId}#PLATFORM#{payload.newPlatform.value}",
                "SK": "LEAGUE_LOOKUP",
                "canonical_league_id": canonical_league_id,
                "platform": payload.newPlatform.value,
                "league_id": payload.newPlatformLeagueId,
            }
        )

        main.table.put_item(
            Item={
                "PK": f"LEAGUE#{canonical_league_id}",
                "SK": f"PLATFORM_MIGRATION#{platform.value}#{payload.newPlatform.value}",
                "data": payload.managerMapping,
            }
        )

        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression=(
                "SET active_platform = :ap, migrated_from = :mf, "
                "migrated_at = :ma, active_job_id = :ajid, #p = :ap"
            ),
            ExpressionAttributeNames={"#p": "platform"},
            ExpressionAttributeValues={
                ":ap": payload.newPlatform.value,
                ":mf": platform.value,
                ":ma": now_iso,
                ":ajid": correlation_id,
            },
        )
    except botocore.exceptions.ClientError as e:
        logger.error("DynamoDB error during migration setup: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set up migration",
        )

    try:
        invoke_onboarder(
            lambda_client=main.lambda_client,
            function_name=os.environ["ONBOARDER_LAMBDA_NAME"],
            body={
                "leagueId": payload.newPlatformLeagueId,
                "platform": payload.newPlatform.value,
                "season": payload.season,
                "s2": payload.s2,
                "swid": payload.swid,
            },
            request_type="MIGRATE",
            canonical_league_id=canonical_league_id,
            correlation_id=correlation_id,
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


@router.delete("/leagues/{leagueId}", status_code=status.HTTP_200_OK)
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
        response = main.s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=s3_prefix)
        if "Contents" in response:
            delete_keys = [{"Key": obj["Key"]} for obj in response["Contents"]]

            # S3 delete_objects can handle up to 1,000 keys per request
            main.s3_client.delete_objects(
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


@router.get("/leagues/{leagueId}/query", status_code=status.HTTP_200_OK)
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
    require_active_subscription(canonical_league_id)
    pk = f"LEAGUE#{canonical_league_id}"

    try:
        if sk.endswith("#"):
            items: list[Any] = []
            kwargs: dict[str, Any] = {
                "KeyConditionExpression": Key("PK").eq(pk) & Key("SK").begins_with(sk),
            }
            while True:
                db_response = main.table.query(**kwargs)
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
            db_response = main.table.get_item(
                Key={"PK": pk, "SK": sk}, ConsistentRead=True
            )
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
