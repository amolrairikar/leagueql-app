"""FastAPI route registration for the LeagueQL API.

Handlers live in the submodules, grouped by domain; each exposes an
``APIRouter`` that is combined here into the single ``router`` ``main`` includes on
the app. AWS clients (``table``, ``lambda_client``, ``s3_client``) and the
``http_requests`` module are reached through ``main`` at call time so test patches
on ``main.table`` etc. take effect in the handlers.

Packaged into the Lambda zip as a subpackage by
``scripts/deployment_scripts/build_lambda_zip.sh``.
"""

from fastapi import APIRouter

from . import leagues, management, onboarding, sharing, system, yahoo_oauth

router = APIRouter()
for _sub in (system, leagues, onboarding, management, sharing, yahoo_oauth):
    router.include_router(_sub.router)
