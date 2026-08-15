"""LeagueQL API application assembly.

Holds shared infrastructure (logging, FastAPI app, AWS clients, config) plus the
request/response models and enums. Helper functions live in ``helpers.py`` and
route handlers in ``routes.py``; both are wired together here. Helper functions
are re-exported from this module so ``main.<helper>`` remains the public surface.
"""

import os
from enum import Enum
from typing import Any, Optional

import boto3
import botocore.config
import requests as http_requests  # noqa: F401  re-exported for test patch points
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel, ConfigDict, Field

# Re-exported so ``main.<name>`` stays the public surface for helpers, routes,
# and tests (e.g. ``from main import correlation_id_var, JsonFormatter``).
from common.logging_utils import (  # noqa: F401
    JsonFormatter,
    correlation_id_var,
    logger,
    setup_logger,
)


def _parse_cors_origins(raw: str) -> list[str]:
    """Parse the comma-separated ``CORS_ALLOW_ORIGINS`` env var.

    Terraform sets this per environment (dev additionally trusts the local Vite
    dev origin; prod trusts only the live site), keeping the FastAPI middleware in
    lockstep with the API Gateway CORS config. When the var is unset/empty this
    **fails closed** to the production origin only, so a misconfiguration never
    silently trusts ``http://localhost`` in production.
    """
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["https://leagueql.com"]


ORIGINS = _parse_cors_origins(os.environ.get("CORS_ALLOW_ORIGINS", ""))


class APIResponse(BaseModel):
    detail: str
    data: Optional[Any] = None


class QueryResponse(BaseModel):
    data: list[Any]


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
    TRANSACTIONS = "TRANSACTIONS"
    PLATFORM_MIGRATION = "PLATFORM_MIGRATION"


QUERY_TYPE_TO_SK_BASE = {
    QueryType.TEAMS: "TEAMS",
    QueryType.MATCHUPS: "MATCHUPS",
    QueryType.SEASON_STANDINGS: "STANDINGS",
    QueryType.WEEKLY_STANDINGS: "WEEKLY_STANDINGS",
    QueryType.PLAYOFF_BRACKET: "PLAYOFF_BRACKET",
    QueryType.DRAFT: "DRAFT",
    QueryType.TRANSACTIONS: "TRANSACTIONS",
    QueryType.PLATFORM_MIGRATION: "PLATFORM_MIGRATION",
}


class EspnMembersPayload(BaseModel):
    swid: str
    s2: str


class ClaimOwnershipPayload(BaseModel):
    token: str = Field(max_length=512)


class ManagerMappingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currentPlatformOwnerId: str = Field(max_length=100)
    newPlatformOwnerId: str = Field(max_length=100)
    displayName: str = Field(max_length=200)


class MigratePayload(BaseModel):
    newPlatformLeagueId: str = Field(max_length=100)
    newPlatform: Platform
    season: Optional[str] = Field(default=None, max_length=10)
    s2: Optional[str] = Field(default=None)
    swid: Optional[str] = Field(default=None, max_length=100)
    managerMapping: list[ManagerMappingEntry] = Field(
        default_factory=list, max_length=64
    )


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    # ``traceparent``/``tracestate`` allow the browser OTel SDK (FE-029) to send W3C
    # trace context cross-origin so the API span continues the browser's trace
    # (BE-020); kept in lockstep with the API Gateway CORS config.
    allow_headers=["Authorization", "Content-Type", "traceparent", "tracestate"],
)

# --- Security response headers (BE-024) --------------------------------------
# Stamped on every response by the middleware below. This is a JSON API (no HTML
# rendering) reached cross-origin via fetch from the SPA, so these are
# defense-in-depth for the edge case where a browser is tricked into treating an
# API response as a document:
#   - nosniff  stops a JSON body being MIME-sniffed into executable HTML/JS.
#   - CSP      locks everything to 'none' so an accidental/error HTML body is
#              inert and the response can't be framed (frame-ancestors 'none').
#   - HSTS     pins HTTPS so the bearer (Clerk JWT) never rides a plaintext
#              request an active MITM could downgrade/strip.
#   - X-Frame-Options  legacy clickjacking cover for browsers that ignore
#                      CSP frame-ancestors.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Frame-Options": "DENY",
}


@app.middleware("http")
async def _security_headers(request, call_next):
    """Stamp security headers on every response and default caching to deny (BE-024).

    Uses ``setdefault`` so route-level intent always wins: ``GET
    /leagues/{id}/query`` keeps its ``private, max-age=300`` opt-in, while every
    other response — including secret-bearing ones like ``POST
    /leagues/{id}/transfer-token`` — falls back to ``no-store``. This default-deny
    is the outcome of the Cache-Control audit: authenticated/private responses are
    never cacheable unless a route deliberately opts in.
    """
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    response.headers.setdefault("Cache-Control", "no-store")
    return response


REFRESH_COOLDOWN_MINUTES = 30

SLEEPER_STATE_URL = "https://api.sleeper.app/v1/state/nfl"

DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]

_retry_config = botocore.config.Config(retries={"mode": "standard"})
dynamodb_resource = boto3.resource("dynamodb", config=_retry_config)
table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)

lambda_client = boto3.client("lambda", config=_retry_config)

s3_client = boto3.client("s3", config=_retry_config)
S3_BUCKET = os.environ["S3_BUCKET_NAME"]

# Minimum interval between `last_accessed_at` writes for a single league (BE-018).
# `get_league` already reads METADATA, so a fresher timestamp short-circuits the write;
# this caps the tracking writes to at most one per league per hour by default.
LEAGUE_ACCESS_THROTTLE_SECONDS = int(
    os.environ.get("LEAGUE_ACCESS_THROTTLE_SECONDS", "3600")
)


# Re-export helpers so ``main.<helper>`` stays the public surface. Imported after
# the infrastructure above so helpers can resolve ``main`` attributes at call time.
from helpers import (  # noqa: E402, F401
    _query_all_keys,
    add_league_member,
    collect_league_keys,
    convert_decimals,
    create_job_status,
    delete_all_league_items,
    get_job_status,
    get_latest_stored_matchup,
    get_league_metadata,
    get_league_seasons,
    get_nfl_state,
    is_job_in_progress,
    lookup_league,
    publish_failure,
    record_league_access,
    require_league_member,
    require_league_owner,
    set_active_job,
    update_league_count,
)

# ``delete_league`` is re-exported because external scripts/integration tests
# call it directly (scripts/utility_scripts/delete_test_league.py).
from routes import delete_league, router  # noqa: E402, F401

app.include_router(router)

# OpenTelemetry distributed tracing → Better Stack (BE-020). A no-op unless the OTLP
# endpoint + token (SSM) are configured, so tests / local / unconfigured envs are
# unaffected. Must run before Mangum wraps the app so request-flush middleware and
# FastAPI instrumentation are in place.
from telemetry import init_tracing  # noqa: E402

init_tracing(app)

handler = Mangum(app)
