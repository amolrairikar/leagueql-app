import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "recap_drainer"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_recap_drainer():
    """Load the drainer handler under a unique name with boto3 mocked.

    The handler creates a DynamoDB resource + S3 client at import and pulls in
    ``common.bedrock`` (which creates a ``bedrock`` client at import); all are mocked
    so no AWS credentials/network are needed. ``RECAP_MIN_BATCH_RECORDS`` is read at
    import, so default it to 1 (submit eagerly); tests that exercise the hold path
    patch ``_MIN_BATCH_RECORDS`` directly.
    """
    env = {
        "DYNAMODB_TABLE_NAME": "test-table",
        "BEDROCK_MODEL_ID": "us.meta.llama3-3-70b-instruct-v1:0",
        "RECAP_BATCH_BUCKET": "test-bucket",
        "RECAP_BATCH_ROLE_ARN": "arn:aws:iam::1:role/batch",
        "RECAP_MIN_BATCH_RECORDS": "1",
        "RECAP_STALE_INFLIGHT_HOURS": "6",
    }
    with patch.dict(os.environ, env):
        with (
            patch("boto3.client") as mock_client,
            patch("boto3.resource") as mock_resource,
        ):
            mock_client.return_value = MagicMock()
            mock_resource.return_value.Table.return_value = MagicMock()
            _load_module("recap_drainer.handler", _SRC / "handler.py")
    yield


@pytest.fixture
def drainer():
    return sys.modules["recap_drainer.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "us.meta.llama3-3-70b-instruct-v1:0")
    monkeypatch.setenv("RECAP_BATCH_BUCKET", "test-bucket")
    monkeypatch.setenv("RECAP_BATCH_ROLE_ARN", "arn:aws:iam::1:role/batch")


@pytest.fixture(autouse=True)
def enable_billing_and_premium():
    from common import feature_flags

    feature_flags._override_for_testing({"billing": True, "premium_feature": True})
    yield
    feature_flags._override_for_testing({"billing": False, "premium_feature": False})
