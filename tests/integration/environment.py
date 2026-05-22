import importlib.util
import os
import sys
import types
from pathlib import Path

import boto3

_ONBOARDER_SRC = Path(__file__).parents[2] / "src" / "onboarder"
_SLEEPER_REFRESH_SRC = Path(__file__).parents[2] / "src" / "sleeper_refresh"
_API_SRC = Path(__file__).parents[2] / "src" / "api"

_REQUIRED_ENV_VARS = ["TEST_SLEEPER_LEAGUE_ID", "AWS_ACCOUNT_ID"]


def _load_module(unique_name, path):
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _cleanup_test_league(test_league_id: str) -> None:
    from fastapi import HTTPException
    from main import Platform, delete_league

    try:
        delete_league(leagueId=test_league_id, platform=Platform.SLEEPER)
    except HTTPException as e:
        if e.status_code != 404:
            raise


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

    if str(_API_SRC) not in sys.path:
        sys.path.insert(0, str(_API_SRC))

    _cleanup_test_league(test_league_id)

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
