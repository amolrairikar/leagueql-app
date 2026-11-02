"""League read endpoints: metadata, membership listing, job status, query and export."""

import contextvars
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

import botocore.exceptions
import espn_credentials
import main
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
    convert_decimals,
    get_job_status,
    get_league_metadata,
    get_league_seasons,
    list_user_leagues,
    lookup_league,
    read_view,
    record_league_access,
    record_sleeper_league_open,
    require_league_member,
)
from main import (
    EXPORT_SEASON_VIEWS,
    PREFIX_READ_QUERY_TYPES,
    QUERY_TYPE_TO_SK_BASE,
    APIResponse,
    ExportResponse,
    Platform,
    QueryResponse,
    QueryType,
    logger,
)

router = APIRouter()


@router.get("/leagues/{leagueId}", status_code=status.HTTP_200_OK)
def get_league(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    response: Response,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Gets league by league ID and platform.

    Sleeper reads stay open; ESPN reads are member-gated (backend/league-authorization) — a
    non-member is rejected with 403 before any league metadata is returned. The
    response includes ``is_owner`` so the frontend can gate owner-only actions.
    """
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    logger.info(
        "Canonical league for league ID %s and platform %s: %s",
        leagueId,
        platform,
        canonical_league_id,
    )
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_member(
        canonical_league_id, clerk_user_id, platform, metadata=metadata
    )
    record_league_access(canonical_league_id, metadata)
    effective_platform = metadata.get("active_platform") or metadata.get("platform")
    # Sleeper reads are open, so opening one is how a viewer joins their league list
    # (backend/user-leagues). Best-effort; never affects this response.
    if effective_platform == Platform.SLEEPER.value:
        record_sleeper_league_open(canonical_league_id, clerk_user_id)
    seasons = get_league_seasons(canonical_league_id=canonical_league_id)
    is_owner = metadata.get("owner_user_id") == clerk_user_id
    # Tell the owner of an auto-refreshed ESPN league when its stored cookies were rejected (or
    # are missing), since the scheduled refresh can't proceed until they re-enter them
    # (backend/league-metadata). Never computed for other callers, so nothing leaks to members.
    espn_reauth_required, espn_credentials_failed_at = False, None
    if (
        is_owner
        and effective_platform == Platform.ESPN.value
        and metadata.get("auto_refresh_enabled")
    ):
        espn_reauth_required, espn_credentials_failed_at = (
            espn_credentials.get_reauth_status(clerk_user_id)
        )
    response.headers["Cache-Control"] = "no-store"
    return APIResponse(
        detail="Found league",
        data={
            "seasons": seasons,
            "league_name": metadata.get("league_name"),
            "is_owner": is_owner,
            # Frontend derives data freshness as last_refresh_at ?? onboarded_at:
            # last_refresh_at is absent until the league's first successful refresh.
            "last_refresh_at": metadata.get("last_refresh_at"),
            "onboarded_at": metadata.get("onboarded_at"),
            # Drives the auto-refresh checkbox prefill / sidebar toggle
            # (backend/scheduled-league-auto-refresh). Absent on older leagues → not enrolled.
            "auto_refresh_enabled": bool(metadata.get("auto_refresh_enabled")),
            "espn_reauth_required": espn_reauth_required,
            "espn_credentials_failed_at": espn_credentials_failed_at,
            # Yahoo seasons whose weekly lineups are still being backfilled, or whose backfill
            # couldn't finish yet (backend/yahoo-lineup-backfill); drives the lineup bell.
            "pending_lineup_seasons": sorted(
                metadata.get("pending_lineup_seasons", []), key=int
            ),
            "failed_lineup_seasons": sorted(
                metadata.get("failed_lineup_seasons", []), key=int
            ),
        },
    )


@router.get("/me/leagues", status_code=status.HTTP_200_OK)
def get_my_leagues(
    response: Response,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """List every league the caller owns, joined by invite, or opened on Sleeper.

    Backed by the per-user membership index (backend/user-leagues). Each entry carries the
    league's current platform + league id (enough to open it), unified seasons, last-updated
    time, migration source, and an owner-only ESPN re-auth flag. Newest first.
    """
    leagues = list_user_leagues(clerk_user_id, espn_credentials.get_reauth_status)
    response.headers["Cache-Control"] = "no-store"
    return APIResponse(detail=f"Found {len(leagues)} league(s)", data=leagues)


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


@router.get("/leagues/{leagueId}/query", status_code=status.HTTP_200_OK)
def query_league(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    queryType: Annotated[str, Query(description="The precomputed view to retrieve")],
    response: Response,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> QueryResponse:
    """Returns a precomputed data view for the specified league.

    ESPN queries are member-gated (backend/league-authorization); Sleeper queries stay open.
    """
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

    # A chunked view (transactions) is stored across multiple {BASE}#{season}#{chunk}
    # items, so even a season-suffixed query must resolve via a begins_with prefix scan
    # that concatenates the chunks. The prefix (no trailing "#") also matches any legacy
    # single-key {BASE}#{season} item written before chunking. Every other suffixed view
    # is a single item read with an exact get_item.
    use_prefix_query = sk.endswith("#") or base_type in PREFIX_READ_QUERY_TYPES

    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_member(
        canonical_league_id, clerk_user_id, platform, metadata=metadata
    )

    data = read_view(canonical_league_id, sk_base, suffix, use_prefix=use_prefix_query)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found for the requested query",
        )
    response.headers["Cache-Control"] = "no-store"
    return QueryResponse(data=convert_decimals(data))


# Upper bound on concurrent DynamoDB reads while building an export. Kept under boto3's default
# connection pool (10) so a worker never waits on a pooled connection.
EXPORT_READ_WORKERS = 8


def _read_export_views(
    canonical_league_id: str, seasons: list[str]
) -> dict[tuple[str, str], list | None]:
    """Read every (season, view) pair of an export concurrently.

    Reads are independent and I/O bound, so they run on a bounded thread pool instead of
    serially. Results are keyed by ``(season, view_name)``, so the caller assembles the
    bundle in request order regardless of which read finishes first. Each task runs in a
    copy of the caller's context so OTel DynamoDB spans stay children of the request span.
    The first failed read re-raises its ``HTTPException`` and cancels reads not yet started,
    so no partial bundle is built.
    """
    pool = ThreadPoolExecutor(max_workers=EXPORT_READ_WORKERS)
    try:
        futures = {
            (season, view_name): pool.submit(
                contextvars.copy_context().run,
                read_view,
                canonical_league_id,
                QUERY_TYPE_TO_SK_BASE[query_type],
                season,
                use_prefix=use_prefix,
            )
            for season in seasons
            for view_name, (query_type, use_prefix) in EXPORT_SEASON_VIEWS.items()
        }
        return {key: future.result() for key, future in futures.items()}
    finally:
        pool.shutdown(wait=True, cancel_futures=True)


@router.get("/leagues/{leagueId}/export", status_code=status.HTTP_200_OK)
def export_league(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    seasons: Annotated[
        str, Query(description="Comma-separated season years to export, e.g. 2023,2024")
    ],
    response: Response,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> ExportResponse:
    """Export processed views for the selected seasons as a per-season/per-view bundle.

    ESPN/Yahoo exports are member-gated (backend/league-authorization); Sleeper stays open.
    The bundle omits any view with no stored data for a season. Reads reuse the same
    single-item vs. prefix-concat logic as the query endpoint via ``read_view``.
    """
    requested_seasons = [s.strip() for s in seasons.split(",") if s.strip()]
    if not requested_seasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one season must be specified.",
        )

    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_member(
        canonical_league_id, clerk_user_id, platform, metadata=metadata
    )

    available_seasons = set(get_league_seasons(canonical_league_id))
    if not available_seasons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found for the requested seasons",
        )
    selected_seasons = [s for s in requested_seasons if s in available_seasons]
    if not selected_seasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="None of the requested seasons exist for this league.",
        )

    # TEAMS is stored once for the whole league (SK "TEAMS", no season suffix), so it is
    # read a single time here and filtered per season below rather than through read_view.
    try:
        teams_response = main.table.get_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "TEAMS"},
            ConsistentRead=True,
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )
    teams_rows = (teams_response.get("Item") or {}).get("data") or []

    view_reads = _read_export_views(canonical_league_id, selected_seasons)

    bundle: dict[str, dict[str, list]] = {}
    for season in selected_seasons:
        season_views: dict[str, list] = {}
        for view_name in EXPORT_SEASON_VIEWS:
            view_data = view_reads[(season, view_name)]
            if view_data:
                season_views[view_name] = view_data
        season_teams = [r for r in teams_rows if str(r.get("season")) == season]
        if season_teams:
            season_views["teams"] = season_teams
        if season_views:
            bundle[season] = season_views

    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found for the requested seasons",
        )

    response.headers["Cache-Control"] = "no-store"
    return ExportResponse(data=convert_decimals(bundle))
