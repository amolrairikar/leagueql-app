import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "processor"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_processor():
    """Load processor modules into sys.modules with unique names."""
    saved = {n: sys.modules.get(n) for n in ["logging_utils", "queries", "handler"]}
    env = {"DYNAMODB_TABLE_NAME": "test-table"}

    with patch.dict(os.environ, env):
        with (
            patch("boto3.client") as mock_client,
            patch("boto3.resource") as mock_resource,
        ):
            mock_client.return_value = MagicMock()
            mock_resource.return_value.Table.return_value = MagicMock()

            logging_utils_mod = _load_module(
                "processor.logging_utils", _SRC / "logging_utils.py"
            )
            sys.modules["logging_utils"] = logging_utils_mod

            queries_mod = _load_module("processor.queries", _SRC / "queries.py")
            sys.modules["queries"] = queries_mod

            handler_mod = _load_module("processor.handler", _SRC / "handler.py")
            sys.modules["processor.handler"] = handler_mod

    for name, prev in saved.items():
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev

    yield


@pytest.fixture(scope="session")
def processor_handler():
    return sys.modules["processor.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
