import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "recap_completion"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_recap_completion():
    """Load the completion handler under a unique name with boto3 mocked."""
    env = {"DYNAMODB_TABLE_NAME": "test-table"}
    with patch.dict(os.environ, env):
        with (
            patch("boto3.client") as mock_client,
            patch("boto3.resource") as mock_resource,
        ):
            mock_client.return_value = MagicMock()
            mock_resource.return_value.Table.return_value = MagicMock()
            _load_module("recap_completion.handler", _SRC / "handler.py")
    yield


@pytest.fixture
def completion():
    return sys.modules["recap_completion.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
