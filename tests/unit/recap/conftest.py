"""Fixtures for the recap Lambda unit tests.

Loads the recap modules (``highlights`` / ``ai_generate`` / ``validate`` /
``compose`` / ``handler``) from ``src/recap`` under unique module names (their
basenames collide with other Lambdas), registering the flat names in ``sys.modules``
so each module's bare ``import`` (e.g. the handler's ``from compose import ...``,
compose's ``import ai_generate``) resolve. boto3 is mocked at import so module-level
``boto3.resource`` / lazy ``boto3.client`` need no AWS call or credential; the
Bedrock ``converse`` client is patched per test.
"""

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "recap"

# Bare names registered for the duration of the session, in dependency order.
_MODULES = [
    ("highlights", "highlights.py"),
    ("ai_generate", "ai_generate.py"),
    ("validate", "validate.py"),
    ("compose", "compose.py"),
    ("handler", "handler.py"),
]


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_recap():
    saved = {name: sys.modules.get(name) for name, _ in _MODULES}
    env = {"DYNAMODB_TABLE_NAME": "test-table"}

    with patch.dict(os.environ, env):
        with (
            patch("boto3.resource") as mock_resource,
            patch("boto3.client") as mock_client,
        ):
            mock_resource.return_value = MagicMock()
            mock_client.return_value = MagicMock()

            for bare, filename in _MODULES:
                mod = _load_module(f"recap.{bare}", _SRC / filename)
                sys.modules[bare] = mod

    for name, prev in saved.items():
        if prev is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prev

    yield


@pytest.fixture(scope="session")
def recap_highlights():
    return sys.modules["recap.highlights"]


@pytest.fixture(scope="session")
def recap_ai_generate():
    return sys.modules["recap.ai_generate"]


@pytest.fixture(scope="session")
def recap_validate():
    return sys.modules["recap.validate"]


@pytest.fixture(scope="session")
def recap_compose():
    return sys.modules["recap.compose"]


@pytest.fixture(scope="session")
def recap_handler():
    return sys.modules["recap.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
