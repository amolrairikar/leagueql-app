import importlib.util
import os
import sys
import time
import types
from pathlib import Path

import boto3
import requests

_HERE = Path(__file__).parent
_SRC = Path(__file__).parents[3] / "src"
_ONBOARDER_SRC = _SRC / "onboarder"
_API_SRC = _SRC / "api"

# The dev API Lambda is freshly (re)deployed by the CI job that runs immediately
# before these tests, so the first request can hit a cold container whose init
# exceeds API Gateway's integration window (HTTP 5xx/504) or fails transiently.
# Retry the cleanup DELETE with backoff so a cold start does not fail before_all.
_CLEANUP_MAX_ATTEMPTS = 5
_CLEANUP_BACKOFF_SECONDS = 3

_REQUIRED_ENV_VARS = [
    "TEST_YAHOO_LEAGUE_ID",
    "AWS_ACCOUNT_ID",
    "API_BASE_URL",
    "CLERK_SECRET_KEY_SSM_PARAM",
    "TEST_CLERK_USER_ID",
]

# Token-engine config the in-process onboarder needs (common.yahoo_tokens.from_env()),
# copied from the deployed onboarder so the KMS key/redirect URI never drift from infra.
_YAHOO_ONBOARDER_ENV_VARS = [
    "YAHOO_KMS_KEY_ID",
    "YAHOO_KMS_REGION",
    "YAHOO_CLIENT_ID_SSM_PARAM",
    "YAHOO_REDIRECT_URI",
]


def _load_module(unique_name, path):
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Loaded here (not as a bare import) so the helper resolves regardless of how
# behave sets up sys.path. It only imports ``requests``, so it is safe at import.
mint_jwt = _load_module(
    "yahoo_integration.clerk_auth", _HERE / "clerk_auth.py"
).mint_jwt


def _copy_onboarder_yahoo_env() -> None:
    """Populate the Yahoo token-engine env vars from the deployed onboarder Lambda.

    Explicitly-set env vars win (``setdefault``), so a local run can override them.
    """
    lambda_client = boto3.client("lambda", region_name="us-east-1")
    config = lambda_client.get_function_configuration(
        FunctionName=os.environ["ONBOARDER_LAMBDA_NAME"]
    )
    deployed = config.get("Environment", {}).get("Variables", {})
    for name in _YAHOO_ONBOARDER_ENV_VARS:
        if name in deployed:
            os.environ.setdefault(name, deployed[name])
    missing = [v for v in _YAHOO_ONBOARDER_ENV_VARS[:3] if not os.environ.get(v)]
    if missing:
        raise OSError(
            f"Missing Yahoo onboarder environment variables: {', '.join(missing)}"
        )


def _yahoo_token_key(context) -> dict:
    return {
        "PK": {"S": f"USER#{context.clerk_user_id}"},
        "SK": {"S": "YAHOO_OAUTH"},
    }


def _snapshot_yahoo_token(context) -> dict:
    """Read the test user's (still-encrypted) linked Yahoo token item.

    The cleanup DELETE removes the owner's ``YAHOO_OAUTH`` item when the test league
    is their last Yahoo league (backend/delete-league), so it is captured here and
    restored afterward. The onboarder refreshes/re-stores it as usual, so DynamoDB
    always holds the newest token and no credential lives outside the table.
    """
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name, Key=_yahoo_token_key(context)
    )
    item = resp.get("Item")
    if not item:
        raise OSError(
            f"No YAHOO_OAUTH item for test user {context.clerk_user_id} in "
            f"{context.table_name}. Bootstrap it once by linking Yahoo as the test user "
            "in dev, or by copying an existing dev USER#<id>/YAHOO_OAUTH item with the "
            "PK changed to the test user (same KMS key, so it decrypts as-is). The linked "
            "Yahoo account must be a member of TEST_YAHOO_LEAGUE_ID."
        )
    return item


def _cleanup_test_league(context, test_league_id: str) -> None:
    """Delete any prior onboarded state for the test league via the deployed API.

    Hits ``DELETE /leagues/{id}`` on the dev API Gateway with a Clerk-authed bearer
    token, so the cleanup exercises the real authorizer + Lambda path rather than
    calling the route handler in-process. A 404 means nothing was onboarded — that
    is tolerated, matching the previous in-process cleanup's behavior.

    Retries transient cold-start failures (5xx / connection errors) with backoff;
    a 4xx (e.g. auth failure) is surfaced immediately rather than retried.
    """
    jwt = mint_jwt(
        secret_key=context.clerk_secret_key,
        user_id=context.clerk_user_id,
        template=context.clerk_template,
    )
    url = f"{context.api_base_url}/leagues/{test_league_id}"
    headers = {"Authorization": f"Bearer {jwt}"}
    last_error: Exception | None = None
    for attempt in range(1, _CLEANUP_MAX_ATTEMPTS + 1):
        try:
            resp = requests.delete(
                url,
                params={"platform": "YAHOO"},  # Platform enum is case-insensitive
                headers=headers,
                timeout=30,
            )
            if resp.status_code in (200, 404):
                return
            if resp.status_code < 500:
                # Non-transient (auth/validation) — fail fast.
                resp.raise_for_status()
            last_error = requests.HTTPError(
                f"{resp.status_code} Server Error for DELETE {url}", response=resp
            )
        except requests.exceptions.RequestException as e:
            last_error = e
        if attempt < _CLEANUP_MAX_ATTEMPTS:
            time.sleep(_CLEANUP_BACKOFF_SECONDS * attempt)
    raise last_error


def before_all(context):
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise OSError(f"Missing required environment variables: {', '.join(missing)}")

    os.environ.setdefault("DYNAMODB_TABLE_NAME", "leagueql-table-dev")
    os.environ.setdefault("ONBOARDER_LAMBDA_NAME", "leagueql-onboarder-dev")
    os.environ["S3_BUCKET_NAME"] = (
        f"leagueql-dev-bucket-east-{os.environ['AWS_ACCOUNT_ID']}"
    )
    _copy_onboarder_yahoo_env()

    test_league_id = os.environ["TEST_YAHOO_LEAGUE_ID"]

    # _SRC makes the shared ``common`` package importable; _API_SRC makes ``main`` etc. resolve.
    for path in (_SRC, _API_SRC):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    # Resolve Clerk auth config used to delete the test league through the API.
    from common.secrets import get_ssm_parameter

    context.clerk_secret_key = get_ssm_parameter(
        os.environ["CLERK_SECRET_KEY_SSM_PARAM"]
    )
    context.clerk_user_id = os.environ["TEST_CLERK_USER_ID"]
    context.clerk_template = os.environ.get("CLERK_JWT_TEMPLATE", "integration-tests")
    context.api_base_url = os.environ["API_BASE_URL"].rstrip("/")

    context.table_name = os.environ["DYNAMODB_TABLE_NAME"]
    context.dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
    context.test_league_id = test_league_id

    # Snapshot → cleanup DELETE (may remove the token) → restore, so the test owner's
    # Yahoo link survives every run.
    # Restore in ``finally`` so a DELETE that errors after the server already removed
    # the token (e.g. a client timeout) cannot orphan the link for later runs.
    token_item = _snapshot_yahoo_token(context)
    try:
        _cleanup_test_league(context, test_league_id)
    finally:
        context.dynamodb_client.put_item(TableName=context.table_name, Item=token_item)

    # Load onboarder modules so bare-name imports resolve to onboarder's utils/writer/etc.
    onboarder_pkg = types.ModuleType("onboarder")
    onboarder_pkg.__path__ = [str(_ONBOARDER_SRC)]
    sys.modules["onboarder"] = onboarder_pkg

    onboarder_utils = _load_module("onboarder.utils", _ONBOARDER_SRC / "utils.py")
    sys.modules["utils"] = onboarder_utils

    writer_mod = _load_module("onboarder.writer", _ONBOARDER_SRC / "writer.py")
    sys.modules["writer"] = writer_mod

    # onboarding_service imports all three platform clients under their bare names.
    espn_client_mod = _load_module(
        "onboarder.espn_client", _ONBOARDER_SRC / "espn_client.py"
    )
    sys.modules["espn_client"] = espn_client_mod

    sleeper_client_mod = _load_module(
        "onboarder.sleeper_client", _ONBOARDER_SRC / "sleeper_client.py"
    )
    sys.modules["sleeper_client"] = sleeper_client_mod

    yahoo_client_mod = _load_module(
        "onboarder.yahoo_client", _ONBOARDER_SRC / "yahoo_client.py"
    )
    sys.modules["yahoo_client"] = yahoo_client_mod

    _load_module("onboarding_service", _ONBOARDER_SRC / "onboarding_service.py")

    onboarder_handler_mod = _load_module(
        "onboarder.handler", _ONBOARDER_SRC / "handler.py"
    )

    context.onboarder_handler_mod = onboarder_handler_mod
