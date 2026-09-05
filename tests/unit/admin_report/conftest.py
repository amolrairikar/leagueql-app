import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "admin_report"

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
    """Load the handler with boto3, env, and the SSM webhook resolved to test values.

    The handler creates a DynamoDB resource ``Table`` and resolves the Discord webhook
    from SSM at import time, so both must be patched before the module is first loaded
    (see tests/CLAUDE.md). ``aggregations`` is loaded under a unique name first so the
    handler's bare ``from aggregations import ...`` resolves to it.
    """
    saved = {n: sys.modules.get(n) for n in ["aggregations", "handler"]}
    env = {
        "DYNAMODB_TABLE_NAME": "leagueql-table-test",
        "DISCORD_WEBHOOK_URL_SSM_PARAM": "/leagueql/test/discord/webhook_url",
    }
    with (
        patch.dict(os.environ, env),
        patch("boto3.resource") as mock_resource,
        patch("common.secrets.get_ssm_parameter", return_value=TEST_WEBHOOK_URL),
    ):
        mock_resource.return_value.Table.return_value = MagicMock()
        agg_mod = _load_module("admin_report.aggregations", _SRC / "aggregations.py")
        sys.modules["aggregations"] = agg_mod

        handler_mod = _load_module("admin_report.handler", _SRC / "handler.py")
        sys.modules["handler"] = handler_mod

    for name, prev in saved.items():
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev

    yield


@pytest.fixture
def handler():
    return sys.modules["admin_report.handler"]


@pytest.fixture
def mock_table(handler):
    """Replace the handler's module-level DynamoDB table with a fresh mock."""
    table = MagicMock()
    with patch.object(handler, "_TABLE", table):
        yield table


@pytest.fixture
def mock_post(handler):
    """Patch the handler's HTTP session POST with a default 204 success response."""
    with patch.object(handler._session, "post") as post:
        post.return_value.status_code = 204
        post.return_value.raise_for_status.return_value = None
        yield post
