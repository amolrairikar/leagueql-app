import importlib.util
import os
import sys
import types
from pathlib import Path

import boto3
import requests

_HERE = Path(__file__).parent
_SRC = Path(__file__).parents[3] / "src"
_ONBOARDER_SRC = _SRC / "onboarder"
_SLEEPER_REFRESH_SRC = _SRC / "sleeper_refresh"
_API_SRC = _SRC / "api"

_REQUIRED_ENV_VARS = [
    "TEST_SLEEPER_LEAGUE_ID",
    "AWS_ACCOUNT_ID",
    "API_BASE_URL",
    "CLERK_SECRET_KEY_SSM_PARAM",
    "TEST_CLERK_USER_ID",
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
    "sleeper_integration.clerk_auth", _HERE / "clerk_auth.py"
).mint_jwt


def _cleanup_test_league(context, test_league_id: str) -> None:
    """Delete any prior onboarded state for the test league via the deployed API.

    Hits ``DELETE /leagues/{id}`` on the dev API Gateway with a Clerk-authed bearer
    token, so the cleanup exercises the real authorizer + Lambda path rather than
    calling the route handler in-process. A 404 means nothing was onboarded — that
    is tolerated, matching the previous in-process cleanup's behavior.
    """
    jwt = mint_jwt(
        secret_key=context.clerk_secret_key,
        user_id=context.clerk_user_id,
        template=context.clerk_template,
    )
    resp = requests.delete(
        f"{context.api_base_url}/leagues/{test_league_id}",
        params={"platform": "SLEEPER"},  # Platform enum is case-insensitive
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=30,
    )
    if resp.status_code not in (200, 404):
        resp.raise_for_status()


def before_all(context):
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    os.environ.setdefault("DYNAMODB_TABLE_NAME", "leagueql-table-dev")
    os.environ.setdefault("ONBOARDER_LAMBDA_NAME", "leagueql-onboarder-dev")
    os.environ["S3_BUCKET_NAME"] = (
        f"leagueql-dev-bucket-east-{os.environ['AWS_ACCOUNT_ID']}"
    )

    test_league_id = os.environ["TEST_SLEEPER_LEAGUE_ID"]

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

    _cleanup_test_league(context, test_league_id)

    # Load onboarder modules first so bare-name imports resolve to onboarder's utils/writer/etc.
    onboarder_pkg = types.ModuleType("onboarder")
    onboarder_pkg.__path__ = [str(_ONBOARDER_SRC)]
    sys.modules["onboarder"] = onboarder_pkg

    onboarder_utils = _load_module("onboarder.utils", _ONBOARDER_SRC / "utils.py")
    sys.modules["utils"] = onboarder_utils

    writer_mod = _load_module("onboarder.writer", _ONBOARDER_SRC / "writer.py")
    sys.modules["writer"] = writer_mod

    espn_client_mod = _load_module(
        "onboarder.espn_client", _ONBOARDER_SRC / "espn_client.py"
    )
    sys.modules["espn_client"] = espn_client_mod

    sleeper_client_mod = _load_module(
        "onboarder.sleeper_client", _ONBOARDER_SRC / "sleeper_client.py"
    )
    sys.modules["sleeper_client"] = sleeper_client_mod

    _load_module("onboarding_service", _ONBOARDER_SRC / "onboarding_service.py")

    onboarder_handler_mod = _load_module(
        "onboarder.handler", _ONBOARDER_SRC / "handler.py"
    )

    # Load sleeper_refresh after onboarder; handler uses sleeper_refresh.utils (qualified), not bare utils.
    pkg = types.ModuleType("sleeper_refresh")
    pkg.__path__ = [str(_SLEEPER_REFRESH_SRC)]
    sys.modules["sleeper_refresh"] = pkg

    utils_mod = _load_module("sleeper_refresh.utils", _SLEEPER_REFRESH_SRC / "utils.py")
    sys.modules["utils"] = utils_mod
    handler_mod = _load_module(
        "sleeper_refresh.handler", _SLEEPER_REFRESH_SRC / "handler.py"
    )
    sys.modules["handler"] = handler_mod

    context.onboarder_handler_mod = onboarder_handler_mod
    context.handler_mod = handler_mod
    context.table_name = "leagueql-table-dev"
    context.dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
    context.test_league_id = test_league_id
