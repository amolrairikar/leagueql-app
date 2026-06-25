import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "recap_generator"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_recap_generator():
    """Load the recap-generator handler under a unique name with boto3 mocked.

    The handler creates a DynamoDB resource at import and pulls in ``common.bedrock``
    (which creates a ``bedrock-runtime`` client at import); both are mocked so no AWS
    credentials/network are needed in CI.
    """
    env = {
        "DYNAMODB_TABLE_NAME": "test-table",
        "BEDROCK_MODEL_ID": "meta.llama3-3-70b-instruct-v1:0",
    }
    with patch.dict(os.environ, env):
        with (
            patch("boto3.client") as mock_client,
            patch("boto3.resource") as mock_resource,
        ):
            mock_client.return_value = MagicMock()
            mock_resource.return_value.Table.return_value = MagicMock()
            _load_module("recap_generator.handler", _SRC / "handler.py")
    yield


@pytest.fixture
def recap_handler():
    return sys.modules["recap_generator.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "meta.llama3-3-70b-instruct-v1:0")


@pytest.fixture(autouse=True)
def enable_billing_and_premium():
    """Recaps are billing+premium gated. Default the gate ON for tests so the
    happy path runs; individual tests flip flags via ``_override_for_testing``."""
    from common import feature_flags

    feature_flags._override_for_testing({"billing": True, "premium_feature": True})
    yield
    feature_flags._override_for_testing({"billing": False, "premium_feature": False})
