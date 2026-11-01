"""League sharing endpoints: ownership transfer and member invites."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import botocore.exceptions
import main
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
    _is_conditional_check_failure,
    add_league_member,
    get_league_metadata,
    index_league_member,
    lookup_league,
    require_league_owner,
)
from main import (
    AcceptInvitePayload,
    APIResponse,
    ClaimOwnershipPayload,
    Platform,
    logger,
)

router = APIRouter()


# How long an outstanding ownership-transfer token stays valid before it expires.
TRANSFER_TOKEN_TTL_HOURS = 24


@router.post("/leagues/{leagueId}/transfer-token", status_code=status.HTTP_200_OK)
def create_transfer_token(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Mint a one-time ownership-transfer token (owner-gated, backend/league-authorization).

    Only the plaintext token is returned (to the owner, once); only its sha256
    hash and a short expiry are stored on METADATA. Minting a new token
    overwrites/invalidates any prior outstanding one.
    """
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_owner(canonical_league_id, clerk_user_id, metadata=metadata)

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = (
        datetime.now(UTC) + timedelta(hours=TRANSFER_TOKEN_TTL_HOURS)
    ).isoformat()
    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression=(
                "SET transfer_token_hash = :h, transfer_token_expires_at = :e"
            ),
            ExpressionAttributeValues={":h": token_hash, ":e": expires_at},
        )
    except botocore.exceptions.ClientError as e:
        logger.error(
            "Failed to store transfer token for %s: %s", canonical_league_id, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transfer token",
        )

    return APIResponse(
        detail="Transfer token created",
        data={"token": token, "expires_at": expires_at},
    )


@router.post("/leagues/{leagueId}/claim-ownership", status_code=status.HTTP_200_OK)
def claim_ownership(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    payload: ClaimOwnershipPayload,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Redeem a transfer token to become the league owner (backend/league-authorization).

    Single-use and race-safe: the owner swap is a conditional ``update_item`` that
    only succeeds while the stored hash still matches, so a concurrent second
    redemption fails the condition. The new owner is also added to ``members``.
    """
    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)

    stored_hash = metadata.get("transfer_token_hash")
    if not stored_hash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transfer token outstanding for this league",
        )

    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    if not hmac.compare_digest(token_hash, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid transfer token",
        )

    expires_at = metadata.get("transfer_token_expires_at")
    expired = True
    if expires_at:
        try:
            expired = datetime.fromisoformat(expires_at) <= datetime.now(UTC)
        except ValueError:
            logger.warning(
                "Unparseable transfer_token_expires_at %r for league %s; treating as expired",
                expires_at,
                canonical_league_id,
            )
    if expired:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Transfer token has expired",
        )

    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression=(
                "SET owner_user_id = :caller ADD members :m "
                "REMOVE transfer_token_hash, transfer_token_expires_at"
            ),
            ConditionExpression="transfer_token_hash = :h",
            ExpressionAttributeValues={
                ":caller": clerk_user_id,
                ":m": {clerk_user_id},
                ":h": stored_hash,
            },
        )
    except botocore.exceptions.ClientError as e:
        if _is_conditional_check_failure(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transfer token already redeemed",
            )
        logger.error("Failed to claim ownership for %s: %s", canonical_league_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to claim ownership",
        )
    # Index the new owner for GET /me/leagues (backend/user-leagues). The previous owner
    # stays in `members` and keeps their own entry.
    index_league_member(canonical_league_id, clerk_user_id)

    return APIResponse(detail="Ownership claimed")


@router.post("/leagues/{leagueId}/invite-token", status_code=status.HTTP_200_OK)
def create_invite_token(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Mint a reusable invite token (owner-gated, backend/league-authorization).

    The owner shares the resulting link with leaguemates; anyone who opens it and
    redeems it via ``accept-invite`` is added to ``members`` without needing their
    own ESPN or Yahoo credentials. Only the plaintext token is returned (to the
    owner, once); only its sha256 hash is stored on METADATA. The token has no
    expiry and is reusable — minting a new one overwrites the stored hash,
    invalidating any previously shared link (revoke-by-regenerate).

    Only applies to gated leagues (ESPN and Yahoo) — Sleeper reads are open, so no
    invite is needed and the request is a 400.
    """
    if platform == Platform.SLEEPER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite links only apply to ESPN and Yahoo leagues",
        )

    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)
    require_league_owner(canonical_league_id, clerk_user_id, metadata=metadata)

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression="SET invite_token_hash = :h",
            ExpressionAttributeValues={":h": token_hash},
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to store invite token for %s: %s", canonical_league_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invite link",
        )

    return APIResponse(detail="Invite link created", data={"token": token})


@router.post("/leagues/{leagueId}/accept-invite", status_code=status.HTTP_200_OK)
def accept_invite(
    leagueId: Annotated[
        str, Path(description="The ID of the fantasy league", pattern=r"^\d+$")
    ],
    platform: Annotated[Platform, Query(description="The platform the league is on")],
    payload: AcceptInvitePayload,
    clerk_user_id: Annotated[str, Depends(get_authenticated_user)],
) -> APIResponse:
    """Redeem an invite token to join a league (backend/league-authorization).

    A signed-in caller submits the token from the owner's invite link; when its
    sha256 hash matches the league's stored ``invite_token_hash`` the caller is
    added to ``members`` (idempotent) and may read the league — no ESPN or Yahoo
    credentials of their own required. The token is reusable: the stored hash is
    left intact so other leaguemates can redeem the same link. The compare is
    constant-time.

    Only applies to gated leagues (ESPN and Yahoo) — Sleeper reads are open, so
    redemption is a 400.
    """
    if platform == Platform.SLEEPER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite links only apply to ESPN and Yahoo leagues",
        )

    canonical_league_id = lookup_league(league_id=leagueId, platform=platform)
    metadata = get_league_metadata(canonical_league_id=canonical_league_id)

    stored_hash = metadata.get("invite_token_hash")
    if not stored_hash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No invite link outstanding for this league",
        )

    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    if not hmac.compare_digest(token_hash, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid invite link",
        )

    add_league_member(canonical_league_id, clerk_user_id)
    logger.info("Redeemed invite link; added user to league %s", canonical_league_id)
    return APIResponse(detail="Invite accepted")
