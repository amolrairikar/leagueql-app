import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "sleeper_refresh"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_sleeper_refresh():
    """Load sleeper_refresh modules into sys.modules with unique names."""
    saved = {n: sys.modules.get(n) for n in ["utils", "handler"]}
    env = {
        "DYNAMODB_TABLE_NAME": "test-table",
        "ONBOARDER_LAMBDA_NAME": "test-onboarder",
    }

    with patch.dict(os.environ, env):
        with patch("boto3.client") as mock_client:
            mock_client.return_value = MagicMock()
            utils_mod = _load_module("sleeper_refresh.utils", _SRC / "utils.py")
            sys.modules["utils"] = utils_mod

            handler_mod = _load_module("sleeper_refresh.handler", _SRC / "handler.py")
            sys.modules["handler"] = handler_mod

    for name, prev in saved.items():
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev

    yield


@pytest.fixture(scope="session")
def sleeper_refresh_utils():
    return sys.modules["sleeper_refresh.utils"]


@pytest.fixture(scope="session")
def sleeper_refresh_handler():
    return sys.modules["sleeper_refresh.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
    monkeypatch.setenv("ONBOARDER_LAMBDA_NAME", "test-onboarder")
