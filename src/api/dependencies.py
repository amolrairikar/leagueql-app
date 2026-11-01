"""Shared FastAPI dependencies for the route modules."""

from fastapi import (
    HTTPException,
    Request,
    status,
)


def get_authenticated_user(request: Request) -> str:
    """Return the authenticated Clerk user ID from the API Gateway JWT authorizer.

    The Clerk JWT is validated by the API Gateway authorizer; its verified claims
    are surfaced to the Lambda under the original event, which Mangum exposes at
    ``request.scope["aws.event"]``. Used as a FastAPI dependency for endpoints
    that must identify the caller (ownership and ESPN read gating).

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
