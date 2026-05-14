import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "onboarder"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_onboarder():
    """Load all onboarder modules into sys.modules with unique names."""
    saved = {
        name: sys.modules.get(name)
        for name in [
            "utils",
            "writer",
            "espn_client",
            "sleeper_client",
            "onboarding_service",
            "handler",
        ]
    }
    env = {"DYNAMODB_TABLE_NAME": "test-table", "S3_BUCKET_NAME": "test-bucket"}

    with patch.dict(os.environ, env):
        with patch("boto3.client") as mock_client:
            mock_client.return_value = MagicMock()

            # Load in dependency order, registering under both bare and unique names
            for bare in [
                "utils",
                "writer",
                "espn_client",
                "sleeper_client",
                "onboarding_service",
            ]:
                mod = _load_module(f"onboarder.{bare}", _SRC / f"{bare}.py")
                sys.modules[bare] = mod

            h_mod = _load_module("onboarder.handler", _SRC / "handler.py")
            sys.modules["handler"] = h_mod

    # Restore bare names so other conftest fixtures can register their own modules
    for name, prev in saved.items():
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev

    yield


@pytest.fixture(scope="session")
def onboarder_utils():
    return sys.modules["onboarder.utils"]


@pytest.fixture(scope="session")
def onboarder_writer():
    return sys.modules["onboarder.writer"]


@pytest.fixture(scope="session")
def onboarder_espn_client():
    return sys.modules["onboarder.espn_client"]


@pytest.fixture(scope="session")
def onboarder_sleeper_client():
    return sys.modules["onboarder.sleeper_client"]


@pytest.fixture(scope="session")
def onboarder_onboarding_service():
    return sys.modules["onboarder.onboarding_service"]


@pytest.fixture(scope="session")
def onboarder_handler():
    return sys.modules["onboarder.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
