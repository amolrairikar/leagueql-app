import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "league_reaper"

TEST_WEBHOOK_URL = "https://discord.com/api/webhooks/123/abc"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_reaper():
    """Load the handler with boto3, env, and the SSM webhook resolved to test values."""
    saved = {n: sys.modules.get(n) for n in ["eligibility"]}
    env = {
        "DYNAMODB_TABLE_NAME": "leagueql-table-test",
        "S3_BUCKET_NAME": "leagueql-bucket-test",
        "DISCORD_WEBHOOK_URL_SSM_PARAM": "/leagueql/test/discord/webhook_url",
    }
    with (
        patch.dict(os.environ, env),
        patch("boto3.resource"),
        patch("boto3.client"),
        patch("common.secrets.get_ssm_parameter", return_value=TEST_WEBHOOK_URL),
    ):
        sys.modules["eligibility"] = _load_module(
            "league_reaper.eligibility", _SRC / "eligibility.py"
        )
        _load_module("league_reaper.handler", _SRC / "handler.py")

    for name, prev in saved.items():
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev

    yield


@pytest.fixture
def eligibility():
    return sys.modules["league_reaper.eligibility"]


@pytest.fixture
def handler():
    return sys.modules["league_reaper.handler"]


@pytest.fixture
def mock_table(handler):
    table = MagicMock()
    with patch.object(handler, "_TABLE", table):
        yield table


@pytest.fixture
def mock_post(handler):
    with patch.object(handler._session, "post") as post:
        yield post


@pytest.fixture
def mock_deletion(handler):
    """Replace the shared deletion engine, recording the order of delete calls."""
    with patch.object(handler, "league_deletion") as deletion:
        deletion.owner_has_other_yahoo_leagues.return_value = False
        deletion.owner_has_other_optedin_espn_leagues.return_value = False
        yield deletion


@pytest.fixture
def context():
    ctx = MagicMock()
    ctx.get_remaining_time_in_millis.return_value = 900_000
    return ctx
