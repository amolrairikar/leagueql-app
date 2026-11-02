"""Public system endpoints: liveness check and feature flags."""

from fastapi import (
    APIRouter,
    Response,
    status,
)
from main import (
    APIResponse,
)

from common.feature_flags import BANNER, is_enabled

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
def health() -> APIResponse:
    """Public, unauthenticated liveness check for external uptime probes (backend/health-check-alerting)."""
    return APIResponse(detail="Healthy!")


@router.get("/feature-flags", status_code=status.HTTP_200_OK)
def get_feature_flags(response: Response) -> APIResponse:
    """Return the resolved global feature-flag map for the SPA (backend/feature-flags / frontend/feature-flags).

    Unauthenticated (no Clerk dependency) so it loads before sign-in. The payload
    is only the non-sensitive global booleans the frontend already shipped — the
    same flags the backend itself enforces — so public exposure is fine. The SPA
    fetches this to build its OpenFeature provider; never cache it so a console
    toggle is picked up on the next load.
    """
    response.headers["Cache-Control"] = "no-store"
    return APIResponse(
        detail="Feature flags",
        data={
            BANNER: is_enabled(BANNER),
        },
    )
