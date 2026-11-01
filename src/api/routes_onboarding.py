"""Onboarding endpoints: onboard a league, look up ESPN/Yahoo members, migrate platforms."""

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import botocore.exceptions
import espn_credentials
import main
import requests as http_requests
import yahoo_oauth
from dependencies import get_authenticated_user
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)
from helpers import (
    create_job_status,
    get_latest_stored_matchup,
    get_league_metadata,
    get_nfl_state,
    is_job_in_progress,
    lookup_league,
    require_league_owner,
    set_active_job,
)
from main import (
    REFRESH_COOLDOWN_DAYS,
    APIResponse,
    EspnMembersPayload,
    MigratePayload,
    OnboardingPayload,
    Platform,
    RequestType,
    correlation_id_var,
    logger,
)

from common.onboarder_invoke import invoke_onboarder
from common.yahoo_members import YahooLeagueNotFound, fetch_yahoo_members

router = APIRouter()


def _format_cooldown_wait(remaining: timedelta) -> str:
    """Render the remaining refresh cooldown as a short human-readable phrase.

    Rounds up to whole days when at least a day remains, otherwise falls back to
    whole hours (minimum "1 hour"), so the 429 message reads naturally for the
    weekly (7-day) window rather than as a raw minute count.
    """
    total_seconds = max(remaining.total_seconds(), 0)
    if total_seconds >= 86400:
        # Round partial days up so we never understate the wait.
        days = int(-(-total_seconds // 86400))
        return f"{days} day{'s' if days != 1 else ''}"
    # Under a day: report whole hours, at least "1 hour".
    hours = max(int(-(-total_seconds // 3600)), 1)
    return f"{hours} hour{'s' if hours != 1 else ''}"


def _refresh_block_reason(
    canonical_league_id: str, league_metadata: dict
) -> HTTPException | None:
    """Return the ``409``/``429`` that blocks a refresh of this league, or ``None`` if allowed.

    Covers, in order: a refresh already in progress (409), the weekly cooldown outside DEV (429),
    the NFL offseason (409), and a league already current for the NFL state (409)
    (backend/league-refresh).
    """
    if is_job_in_progress(league_metadata):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A refresh is already in progress for this league",
        )
    last_refresh_at = league_metadata.get("last_refresh_at")
    # The weekly cooldown is disabled in DEV so the refresh pipeline can be
    # iterated on without waiting a week between test refreshes.
    if last_refresh_at and os.environ.get("ENVIRONMENT") != "dev":
        last_refresh_dt = datetime.fromisoformat(last_refresh_at)
        now = datetime.now(UTC)
        # Measure the cooldown in whole UTC calendar days, not an exact 7x24h
        # duration: the intent is "once per week", so a refresh 7 calendar days
        # later is allowed at any time of day. An exact-duration check would
        # wrongly reject a refresh a few hours short of the clock (e.g. last
        # refreshed 10:00, retried 08:00 on day 7).
        elapsed_days = (now.date() - last_refresh_dt.date()).days
        if elapsed_days < REFRESH_COOLDOWN_DAYS:
            allowed_date = last_refresh_dt.date() + timedelta(
                days=REFRESH_COOLDOWN_DAYS
            )
            allowed_at = datetime(
                allowed_date.year,
                allowed_date.month,
                allowed_date.day,
                tzinfo=UTC,
            )
            wait = _format_cooldown_wait(allowed_at - now)
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"This league can only be refreshed once per week. You can refresh again in {wait}.",
            )

    nfl_state = get_nfl_state()
    if nfl_state is not None:
        if nfl_state.get("season_type") == "off":
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="League is already up to date (NFL offseason).",
            )
        state_season = int(nfl_state["season"])
        state_week = int(nfl_state["week"])
        latest = get_latest_stored_matchup(canonical_league_id)
        if latest is not None and latest >= (state_season, state_week):
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="League is already up to date.",
            )
    return None


def _fetch_espn_league_teams(
    espn_league_id: str, season: str, swid: str, s2: str
) -> http_requests.Response:
    """GET an ESPN league's ``mTeam`` view with the caller's cookies, raising on HTTP errors.

    ``espn_league_id`` and ``season`` must already be digit-validated: both are interpolated into
    the upstream ESPN URL.
    """
    espn_url = (
        f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
        f"/seasons/{season}/segments/0/leagues/{espn_league_id}?view=mTeam"
    )
    espn_response = http_requests.get(
        espn_url,
        cookies={"SWID": swid, "espn_s2": s2},
        timeout=10,
    )
    espn_response.raise_for_status()
    return espn_response


def _enroll_blocked_espn_auto_refresh(
    payload: OnboardingPayload, canonical_league_id: str, clerk_user_id: str
) -> None:
    """Enroll an ESPN league in auto-refresh when its opted-in refresh is blocked.

    The onboarder never runs for a blocked refresh, so the cookies are first validated with a
    lightweight ESPN read, then stored encrypted (backend/espn-credential-storage) and
    ``auto_refresh_enabled`` is set on METADATA. Rejected cookies return ``400`` and ESPN
    failures ``502`` with nothing stored; a storage/flag failure returns ``500`` so a 429/409 for
    an opted-in request always means the league is enrolled.
    """
    if not payload.season:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A season is required to enable automatic refresh.",
        )
    try:
        _fetch_espn_league_teams(
            payload.leagueId, payload.season, payload.swid or "", payload.s2 or ""
        )
    except http_requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        if status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your ESPN cookies couldn't be verified. Re-enter your SWID and "
                "espn_s2 and try again.",
            )
        logger.error("ESPN API error verifying auto-refresh cookies: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to verify ESPN cookies",
        )
    except http_requests.exceptions.RequestException as e:
        logger.error("Request error verifying auto-refresh cookies: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach ESPN API",
        )

    # Store the cookies before setting the flag: an enrolled league without stored cookies would
    # fail its next scheduled refresh, while orphaned cookies are simply replaced next time.
    try:
        espn_credentials.store_credentials(clerk_user_id, payload.swid, payload.s2)
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression="SET auto_refresh_enabled = :ar",
            ExpressionAttributeValues={":ar": True},
        )
    except Exception as e:  # noqa: BLE001 - surface any storage failure as a 500
        logger.error(
            "Failed to enable auto-refresh for blocked refresh of %s: %s",
            canonical_league_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable automatic refresh",
        )
    logger.info(
        "Enrolled league %s in auto-refresh despite blocked refresh",
        canonical_league_id,
    )


@router.post("/leagues", status_code=status.HTTP_201_CREATED)
def onboard_league(
    payload: OnboardingPayload,
    response: Response,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
    requestType: Annotated[
        RequestType, Query(description="The type of request: ONBOARD or REFRESH")
    ] = RequestType.ONBOARD,
) -> APIResponse:
    """Onboard a league to the application."""
    correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    platform = Platform(payload.platform)

    if platform == Platform.YAHOO and not yahoo_oauth.has_valid_link(clerk_user_id):
        # Yahoo onboarding/refresh is gated on a linked OAuth token (backend/yahoo-oauth):
        # an unlinked caller gets the "link first" signal the frontend routes to the OAuth
        # step. A linked caller falls through to the normal onboard/refresh path below — the
        # onboarder resolves the Yahoo access token from the owner's Clerk id (no s2/swid).
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Link your Yahoo account first",
        )

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
        require_league_owner(
            canonical_league_id, clerk_user_id, metadata=league_metadata
        )
        blocked = _refresh_block_reason(canonical_league_id, league_metadata)
        if blocked is not None:
            # A blocked refresh still honors an ESPN auto-refresh opt-in: validate and store the
            # supplied cookies and enroll the league, then return the original 429/409 so the
            # caller learns the data itself wasn't refreshed (backend/league-refresh).
            if (
                payload.autoRefresh
                and platform == Platform.ESPN
                and payload.s2
                and payload.swid
            ):
                _enroll_blocked_espn_auto_refresh(
                    payload, canonical_league_id, clerk_user_id
                )
            raise blocked

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
            owner_user_id=clerk_user_id,
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
        str,
        Query(
            description="The ESPN league ID to fetch members from",
            pattern=r"^\d+$",
        ),
    ],
    season: Annotated[
        str, Query(description="The ESPN season year", pattern=r"^\d{4}$")
    ],
    payload: EspnMembersPayload,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Proxy ESPN Fantasy API to fetch league members server-side (avoids browser CORS).

    ``espnLeagueId`` and ``season`` are interpolated into the upstream ESPN URL, so
    both are constrained to digits only (``^\\d+$`` / ``^\\d{4}$``) to keep
    attacker-controlled characters (``?``, ``&``, ``/``, ``..``) out of the request
    path/query — preventing parameter injection / path traversal against the ESPN host.

    Owner-gated (backend/league-authorization): this is the owner's onboarding/migration
    manager-mapping tool. Non-owner league-mates join via an owner's invite link
    (``accept-invite``).
    """
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_owner(canonical_league_id, clerk_user_id, metadata=metadata)

    try:
        espn_response = _fetch_espn_league_teams(
            espnLeagueId, season, payload.swid, payload.s2
        )
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


@router.post("/leagues/{leagueId}/yahoo_members", status_code=status.HTTP_200_OK)
def get_yahoo_members(
    leagueId: Annotated[
        str, Path(description="The ID of the current league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The current platform")],
    yahooLeagueId: Annotated[
        str,
        Query(
            description="The destination Yahoo league ID to fetch members from",
            pattern=r"^\d+$",
        ),
    ],
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Fetch a destination Yahoo league's managers for migration mapping (backend/yahoo-members-proxy).

    Uses the caller's linked user-level Yahoo OAuth token to enumerate their NFL leagues,
    resolve ``yahooLeagueId`` to its ``league_key``, and fetch that league's managers
    server-side — the Yahoo access token never reaches the browser.

    ``yahooLeagueId`` is constrained to digits (``^\\d+$``) so attacker-controlled characters
    (``?``, ``&``, ``/``, ``..``) can't be injected into the upstream Yahoo request path/query.

    Owner-gated (backend/league-authorization): this is the owner's migration manager-mapping
    tool. A caller with no valid Yahoo link (or a revoked refresh token) gets ``403`` so the
    frontend routes to the OAuth link; a league that isn't among the caller's Yahoo leagues gets
    ``404``; Yahoo HTTP/network/parse failures get ``502``.
    """
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_owner(canonical_league_id, clerk_user_id, metadata=metadata)

    try:
        access_token = yahoo_oauth.get_valid_access_token(clerk_user_id)
    except yahoo_oauth.YahooReauthRequired:
        # No valid link, or the stored refresh token was revoked — the frontend routes this
        # 403 to the "Connect with Yahoo" OAuth step (backend/yahoo-oauth).
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Link your Yahoo account first",
        )

    try:
        members = fetch_yahoo_members(
            access_token, yahooLeagueId, http=main.http_requests
        )
    except YahooLeagueNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That Yahoo league isn't in your Yahoo account",
        )
    except http_requests.exceptions.RequestException as e:
        logger.error("Yahoo API error fetching members: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch Yahoo league members",
        )
    except ValueError as e:
        logger.error("Failed to parse Yahoo members response: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse Yahoo API response",
        )

    return APIResponse(detail="Found Yahoo members", data=members)


@router.post("/leagues/{leagueId}/migrate", status_code=status.HTTP_202_ACCEPTED)
def migrate_league(
    leagueId: Annotated[
        str, Path(description="The ID of the current platform league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The current platform")],
    payload: MigratePayload,
    response: Response,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
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
    require_league_owner(canonical_league_id, clerk_user_id, metadata=league_metadata)
    if payload.newPlatform == Platform.YAHOO and not yahoo_oauth.has_valid_link(
        clerk_user_id
    ):
        # A Yahoo destination is onboarded with the owner's linked OAuth token (no cookies).
        # An unlinked caller gets the same "link first" signal the frontend routes to the
        # Yahoo OAuth step (backend/yahoo-oauth); the members proxy uses the same gate.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Link your Yahoo account first",
        )
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

    now_iso = datetime.now(UTC).isoformat()

    try:
        # The destination LEAGUE_LOOKUP is intentionally NOT written here. It is
        # written by the onboarder only after it successfully fetches the
        # destination-platform league (backend/league-migration), so a failed or
        # unauthorized migration can't squat on / deny onboarding of a
        # destination league ID the caller doesn't actually control. Writing it
        # up front (before the onboarder validates access) was the SEC-01 gap.
        main.table.put_item(
            Item={
                "PK": f"LEAGUE#{canonical_league_id}",
                "SK": f"PLATFORM_MIGRATION#{platform.value}#{payload.newPlatform.value}",
                "data": [entry.model_dump() for entry in payload.managerMapping],
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
            # Migration is owner-gated, so the caller is the league owner; the destination
            # onboarder needs this to resolve the owner's Yahoo access token (no-op for
            # ESPN/Sleeper destinations).
            owner_user_id=clerk_user_id,
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
