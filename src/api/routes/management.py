"""League management endpoints: delete a league and set auto-refresh."""

from typing import Annotated

import botocore.exceptions
import espn_credentials
import main
import yahoo_oauth
from dependencies import get_authenticated_user
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from helpers import (
    delete_all_league_items,
    get_league_metadata,
    lookup_league,
    owner_has_other_optedin_espn_leagues,
    owner_has_other_yahoo_leagues,
    publish_failure,
    require_league_owner,
)
from main import (
    S3_BUCKET,
    APIResponse,
    AutoRefreshPayload,
    Platform,
    logger,
)

router = APIRouter()


@router.delete("/leagues/{leagueId}", status_code=status.HTTP_200_OK)
def delete_league(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Deletes an onboarded league."""
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_owner(canonical_league_id, clerk_user_id, metadata=metadata)
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

        # A user's Yahoo OAuth token lives in a single per-user item
        # (USER#{id}/YAHOO_OAUTH), not under the league, because one linked Yahoo
        # account backs all of that user's Yahoo leagues. Deleting a Yahoo league
        # would otherwise orphan those encrypted credentials forever, so once the
        # owner (the only caller who reaches here) has no other Yahoo league we
        # remove the token item too (backend/delete-league, backend/yahoo-oauth).
        # Effective platform uses active_platform (a league migrated *to* Yahoo
        # counts; one migrated *away* does not), falling back to platform.
        #
        # This whole block is best-effort and fully self-contained: the league data
        # is already gone, so NOTHING here — including the GSI3 ownership check —
        # may turn a successful delete into a failure. Any error (a GSI3 IAM/query
        # error, a token delete error, ...) is alerted and swallowed so the caller
        # still sees the delete succeed.
        effective_platform = metadata.get("active_platform") or metadata.get("platform")
        if effective_platform == Platform.YAHOO.value:
            try:
                if not owner_has_other_yahoo_leagues(
                    clerk_user_id, exclude_canonical_league_id=canonical_league_id
                ):
                    yahoo_oauth.delete_tokens(clerk_user_id)
                    logger.info(
                        "Removed orphaned Yahoo OAuth link after owner's last Yahoo "
                        "league delete"
                    )
            except Exception as e:  # noqa: BLE001 - cleanup must never fail the delete
                logger.error(
                    "Yahoo OAuth cleanup failed after deleting league %s: %s",
                    canonical_league_id,
                    e,
                )
                publish_failure(
                    "Failed to clean up Yahoo OAuth token item after deleting league "
                    f"{canonical_league_id}: {e}"
                )

        # A user's stored ESPN cookies live in a single per-user item
        # (USER#{id}/ESPN_CREDENTIALS) — one ESPN session backs all of that user's ESPN
        # leagues — and are only kept while some ESPN league they own is opted into
        # auto-refresh (backend/espn-credential-storage, backend/delete-league). Once the
        # owner has no *other* opted-in ESPN league, remove the credential item. Same
        # best-effort contract as the Yahoo cleanup above: the league data is already gone,
        # so no error here may turn a successful delete into a failure.
        if effective_platform == Platform.ESPN.value:
            try:
                if not owner_has_other_optedin_espn_leagues(
                    clerk_user_id, exclude_canonical_league_id=canonical_league_id
                ):
                    espn_credentials.delete_credentials(clerk_user_id)
                    logger.info(
                        "Removed orphaned ESPN credentials after owner's last opted-in "
                        "ESPN league delete"
                    )
            except Exception as e:  # noqa: BLE001 - cleanup must never fail the delete
                logger.error(
                    "ESPN credential cleanup failed after deleting league %s: %s",
                    canonical_league_id,
                    e,
                )
                publish_failure(
                    "Failed to clean up ESPN credential item after deleting league "
                    f"{canonical_league_id}: {e}"
                )

        return APIResponse(
            detail="Successfully deleted league",
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Error occurred while deleting league: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete league",
        )


@router.put("/leagues/{leagueId}/auto-refresh", status_code=status.HTTP_200_OK)
def set_auto_refresh(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    payload: AutoRefreshPayload,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Enable or disable scheduled auto-refresh for a league (owner only).

    Persists ``auto_refresh_enabled`` on the canonical league's METADATA
    (backend/scheduled-league-auto-refresh). Disabling the owner's last opted-in ESPN league also
    removes their stored ESPN cookies (backend/espn-credential-storage). Enabling ESPN auto-refresh
    still requires fresh cookies, which the frontend supplies through the connect/refresh form; this
    endpoint only records the flag.
    """
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_owner(canonical_league_id, clerk_user_id, metadata=metadata)

    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression="SET auto_refresh_enabled = :ar",
            ExpressionAttributeValues={":ar": payload.enabled},
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to set auto_refresh_enabled for %s: %s", leagueId, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update auto-refresh setting",
        )

    # Turning off the owner's last opted-in ESPN league orphans their stored cookies, so remove
    # them once no other opted-in ESPN league remains. Best-effort: a cleanup failure does not
    # fail the setting change the user just made.
    effective_platform = metadata.get("active_platform") or metadata.get("platform")
    if not payload.enabled and effective_platform == Platform.ESPN.value:
        try:
            if not owner_has_other_optedin_espn_leagues(
                clerk_user_id, exclude_canonical_league_id=canonical_league_id
            ):
                espn_credentials.delete_credentials(clerk_user_id)
                logger.info(
                    "Removed orphaned ESPN credentials after owner opted out of their "
                    "last ESPN league"
                )
        except Exception as e:  # noqa: BLE001 - cleanup must never fail the setting change
            logger.error(
                "ESPN credential cleanup failed after opt-out for league %s: %s",
                canonical_league_id,
                e,
            )
            publish_failure(
                "Failed to clean up ESPN credential item after opt-out for league "
                f"{canonical_league_id}: {e}"
            )

    return APIResponse(
        detail="Auto-refresh enabled" if payload.enabled else "Auto-refresh disabled",
        data={"auto_refresh_enabled": payload.enabled},
    )
