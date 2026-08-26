import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "discord_notifier"

# The webhook URL the handler resolves from SSM at import time, reused by tests.
TEST_WEBHOOK_URL = "https://discord.com/api/webhooks/123/abc"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_handler():
    """Load the handler with the webhook URL resolved to a fixed test value."""
    env = {"DISCORD_WEBHOOK_URL_SSM_PARAM": "/leagueql/test/discord/webhook_url"}
    with (
        patch.dict(os.environ, env),
        patch("common.secrets.get_ssm_parameter", return_value=TEST_WEBHOOK_URL),
    ):
        _load_module("discord_notifier.handler", _SRC / "handler.py")
    yield


@pytest.fixture
def handler():
    return sys.modules["discord_notifier.handler"]


@pytest.fixture
def mock_post(handler):
    """Patch the handler's HTTP session POST with a default 204 success response."""
    with patch.object(handler._session, "post") as post:
        post.return_value.status_code = 204
        post.return_value.raise_for_status.return_value = None
        yield post
