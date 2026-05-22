import importlib.util
import os
import sys
import types
from pathlib import Path

import boto3

_SRC = Path(__file__).parents[2] / "src" / "sleeper_refresh"


def _load_module(unique_name, path):
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


def before_all(context):
    os.environ.setdefault("DYNAMODB_TABLE_NAME", "leagueql-table-dev")
    os.environ.setdefault("ONBOARDER_LAMBDA_NAME", "leagueql-onboarder-dev")

    pkg = types.ModuleType("sleeper_refresh")
    pkg.__path__ = [str(_SRC)]
    sys.modules["sleeper_refresh"] = pkg

    utils_mod = _load_module("sleeper_refresh.utils", _SRC / "utils.py")
    sys.modules["utils"] = utils_mod
    handler_mod = _load_module("sleeper_refresh.handler", _SRC / "handler.py")
    sys.modules["handler"] = handler_mod

    context.handler_mod = handler_mod
    context.table_name = "leagueql-table-dev"
    context.dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
    context.test_league_id = os.environ["TEST_SLEEPER_LEAGUE_ID"]
