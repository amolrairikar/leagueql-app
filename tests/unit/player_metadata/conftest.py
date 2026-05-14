import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "player_metadata"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_player_metadata():
    saved = {n: sys.modules.get(n) for n in ["utils", "handler"]}
    env = {"S3_BUCKET_NAME": "test-bucket"}

    with patch.dict(os.environ, env):
        with patch("boto3.client") as mock_client:
            mock_client.return_value = MagicMock()
            with patch("requests.Session"):
                utils_mod = _load_module("player_metadata.utils", _SRC / "utils.py")
                sys.modules["utils"] = utils_mod

                _load_module("player_metadata.handler", _SRC / "handler.py")

    for name, prev in saved.items():
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev

    yield


@pytest.fixture(scope="session")
def player_metadata_handler():
    return sys.modules["player_metadata.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
