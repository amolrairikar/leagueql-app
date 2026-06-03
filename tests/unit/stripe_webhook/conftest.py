import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "stripe_webhook"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_webhook():
    """Load the webhook handler under a unique name with boto3 mocked."""
    with patch.dict(os.environ, {"DYNAMODB_TABLE_NAME": "test-table"}):
        with patch("boto3.client") as mock_client:
            mock_client.return_value = MagicMock()
            _load_module("stripe_webhook.handler", _SRC / "handler.py")
    yield


@pytest.fixture
def webhook_handler():
    return sys.modules["stripe_webhook.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
