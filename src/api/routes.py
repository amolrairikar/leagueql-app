"""FastAPI route registration for the LeagueQL API.

Handlers live in the ``routes_*`` modules, grouped by domain; each exposes an
``APIRouter`` that is combined here into the single ``router`` ``main`` includes on
the app. AWS clients (``table``, ``lambda_client``, ``s3_client``) and the
``http_requests`` module are reached through ``main`` at call time so test patches
on ``main.table`` etc. take effect in the handlers.
"""

import routes_leagues
import routes_management
import routes_onboarding
import routes_sharing
import routes_system
import routes_yahoo_oauth
from fastapi import APIRouter

router = APIRouter()
for _sub in (
    routes_system,
    routes_leagues,
    routes_onboarding,
    routes_management,
    routes_sharing,
    routes_yahoo_oauth,
):
    router.include_router(_sub.router)
