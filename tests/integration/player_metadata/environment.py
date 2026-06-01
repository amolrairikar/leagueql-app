import importlib.util
import os
import sys
import types
from pathlib import Path

import boto3

_SRC = Path(__file__).parents[3] / "src"
_PLAYER_METADATA_SRC = _SRC / "player_metadata"

_REQUIRED_ENV_VARS = ["AWS_ACCOUNT_ID"]


def _load_module(unique_name, path):
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


def before_all(context):
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    s3_bucket = f"leagueql-dev-bucket-east-{os.environ['AWS_ACCOUNT_ID']}"
    os.environ["S3_BUCKET_NAME"] = s3_bucket

    # Make the shared ``common`` package importable before loading the handler.
    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))

    pkg = types.ModuleType("player_metadata")
    pkg.__path__ = [str(_PLAYER_METADATA_SRC)]
    sys.modules["player_metadata"] = pkg

    utils_mod = _load_module("player_metadata.utils", _PLAYER_METADATA_SRC / "utils.py")
    sys.modules["utils"] = utils_mod

    handler_mod = _load_module(
        "player_metadata.handler", _PLAYER_METADATA_SRC / "handler.py"
    )

    context.handler_mod = handler_mod
    context.s3_client = boto3.client("s3", region_name="us-east-1")
    context.s3_bucket = s3_bucket
