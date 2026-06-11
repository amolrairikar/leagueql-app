"""LeagueQL API application assembly.

Holds shared infrastructure (logging, FastAPI app, AWS clients, config) plus the
request/response models and enums. Helper functions live in ``helpers.py`` and
route handlers in ``routes.py``; both are wired together here. Helper functions
are re-exported from this module so ``main.<helper>`` remains the public surface.
"""

import functools
import os
from enum import Enum
from typing import Any, Optional

import boto3
import botocore.config
import requests as http_requests  # noqa: F401  re-exported for test patch points
import stripe
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
from common.secrets import get_secret_from_env_param


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
    PLATFORM_MIGRATION = "PLATFORM_MIGRATION"


QUERY_TYPE_TO_SK_BASE = {
    QueryType.TEAMS: "TEAMS",
    QueryType.MATCHUPS: "MATCHUPS",
    QueryType.SEASON_STANDINGS: "STANDINGS",
    QueryType.WEEKLY_STANDINGS: "WEEKLY_STANDINGS",
    QueryType.PLAYOFF_BRACKET: "PLAYOFF_BRACKET",
    QueryType.DRAFT: "DRAFT",
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
    allow_headers=["Authorization", "Content-Type"],
)

REFRESH_COOLDOWN_MINUTES = 30

SLEEPER_STATE_URL = "https://api.sleeper.app/v1/state/nfl"

DYNAMODB_TABLE_NAME = os.environ["DYNAMODB_TABLE_NAME"]

_retry_config = botocore.config.Config(retries={"mode": "standard"})
dynamodb_resource = boto3.resource("dynamodb", config=_retry_config)
table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)

lambda_client = boto3.client("lambda", config=_retry_config)

s3_client = boto3.client("s3", config=_retry_config)
S3_BUCKET = os.environ["S3_BUCKET_NAME"]

# Stripe billing (BE-015). Config is environment-specific: DEV is wired with
# sandbox (test) mode credentials/Price IDs and PROD with live mode. The secret
# key is a SecureString SSM parameter fetched by parameter *name* (the value never
# lands in a Lambda env var / TF state / CI); the non-sensitive Price ID and other
# config stay plain env vars.
#
# The key is resolved **lazily on the first Stripe-touching request** rather than
# at module import: the synchronous SSM round-trip dominated cold-start init
# latency, and resolving it at import would also freeze the secret into a SnapStart
# snapshot. ``ensure_stripe_api_key`` is called at each Stripe SDK call site; the
# resolution is cached (``lru_cache``) so warm requests in the same execution
# environment never re-fetch. ``get_secret_from_env_param`` returns ``""`` when
# unconfigured so the module still imports / runs in contexts where billing is not
# set up (e.g. unit tests, which patch ``main.stripe``).
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_TRIAL_PERIOD_DAYS = int(os.environ.get("STRIPE_TRIAL_PERIOD_DAYS", "14"))
STRIPE_CHECKOUT_SUCCESS_URL = os.environ.get(
    "STRIPE_CHECKOUT_SUCCESS_URL", "https://leagueql.com/home?checkout=success"
)
STRIPE_CHECKOUT_CANCEL_URL = os.environ.get(
    "STRIPE_CHECKOUT_CANCEL_URL", "https://leagueql.com/home"
)
STRIPE_BILLING_PORTAL_RETURN_URL = os.environ.get(
    "STRIPE_BILLING_PORTAL_RETURN_URL", "https://leagueql.com/home"
)


@functools.lru_cache(maxsize=1)
def _resolve_stripe_api_key() -> str:
    """Fetch the Stripe secret key from SSM once per execution environment.

    Cached so only the first Stripe-touching request pays the SSM round-trip;
    every later call returns the memoized value. ``cache_clear()`` resets it (used
    by tests).
    """
    return get_secret_from_env_param("STRIPE_SECRET_KEY_SSM_PARAM")


def ensure_stripe_api_key() -> None:
    """Set ``stripe.api_key`` from SSM on first use (BE-015).

    Called at each Stripe SDK call site instead of resolving the key at module
    import, keeping the synchronous SSM fetch off the cold-start init path (and out
    of any SnapStart snapshot). The underlying fetch is memoized, so repeated calls
    within an execution environment are effectively free.
    """
    stripe.api_key = _resolve_stripe_api_key()


# How long a claimed in-flight checkout marker blocks a second checkout before it
# self-heals (BE-015 Idempotency Layer 1). Configurable per environment
# (Terraform sets a shorter window in dev); defaults to 30 minutes.
CHECKOUT_PENDING_TTL_MINUTES = int(os.environ.get("CHECKOUT_PENDING_TTL_MINUTES", "30"))

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
    cancel_league_subscription,
    claim_pending_checkout,
    collect_league_keys,
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
    publish_failure,
    record_league_access,
    require_active_subscription,
    require_league_member,
    require_league_owner,
    set_active_job,
    trial_used_for_league,
    update_league_count,
)

# ``delete_league`` is re-exported because external scripts/integration tests
# call it directly (scripts/utility_scripts/delete_test_league.py).
from routes import delete_league, router  # noqa: E402, F401

app.include_router(router)

handler = Mangum(app)
