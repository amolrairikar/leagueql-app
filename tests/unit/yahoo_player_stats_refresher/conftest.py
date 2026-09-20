import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "yahoo_player_stats_refresher"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_yahoo_refresher():
    saved = {n: sys.modules.get(n) for n in ["utils", "handler"]}
    env = {"S3_BUCKET_NAME": "test-bucket"}

    with patch.dict(os.environ, env), patch("boto3.client") as mock_client:
        mock_client.return_value = MagicMock()
        with patch("requests.Session"):
            utils_mod = _load_module("yahoo_refresher.utils", _SRC / "utils.py")
            sys.modules["utils"] = utils_mod

            _load_module("yahoo_refresher.handler", _SRC / "handler.py")

    for name, prev in saved.items():
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev

    yield


@pytest.fixture(scope="session")
def yahoo_refresher_handler():
    return sys.modules["yahoo_refresher.handler"]


@pytest.fixture(autouse=True)
def refresher_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    # Service-account config is read from SSM by name; point the env vars at param names and stub
    # the SSM read so the handler resolves real string values (matching the deployed shape).
    monkeypatch.setenv(
        "YAHOO_SERVICE_USER_ID_SSM_PARAM", "/leagueql/test/yahoo/service_user_id"
    )
    monkeypatch.setenv(
        "YAHOO_SERVICE_LEAGUE_KEY_SSM_PARAM", "/leagueql/test/yahoo/service_league_key"
    )
    monkeypatch.delenv("SEASON", raising=False)
    monkeypatch.delenv("MAX_PLAYERS", raising=False)
    monkeypatch.delenv("OUTPUT_KEY", raising=False)

    handler = sys.modules.get("yahoo_refresher.handler")
    if handler is not None:
        values = {
            "YAHOO_SERVICE_USER_ID_SSM_PARAM": "svc-user",
            "YAHOO_SERVICE_LEAGUE_KEY_SSM_PARAM": "461.l.999",
        }
        monkeypatch.setattr(
            handler,
            "get_secret_from_env_param",
            lambda env_var: values.get(env_var, ""),
        )
