"""Fixtures for the recap Lambda unit tests.

Loads ``highlights`` / ``generate`` / ``handler`` from ``src/recap`` under unique
module names (their basenames collide with other Lambdas), registering the flat
names in ``sys.modules`` so the handler's ``from generate import ...`` /
``from highlights import ...`` resolve. boto3 is mocked at import so the handler's
module-level ``boto3.resource`` needs no AWS call or credential (recap composition
itself is pure — no AWS, no LLM).
"""

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[3] / "src" / "recap"


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_recap():
    saved = {
        n: sys.modules.get(n) for n in ["highlights", "generate", "snippets", "handler"]
    }
    env = {"DYNAMODB_TABLE_NAME": "test-table"}

    with patch.dict(os.environ, env):
        with (
            patch("boto3.resource") as mock_resource,
            patch("boto3.client") as mock_client,
        ):
            mock_resource.return_value = MagicMock()
            mock_client.return_value = MagicMock()

            highlights_mod = _load_module("recap.highlights", _SRC / "highlights.py")
            sys.modules["highlights"] = highlights_mod

            snippets_mod = _load_module("recap.snippets", _SRC / "snippets.py")
            sys.modules["snippets"] = snippets_mod

            generate_mod = _load_module("recap.generate", _SRC / "generate.py")
            sys.modules["generate"] = generate_mod

            handler_mod = _load_module("recap.handler", _SRC / "handler.py")
            sys.modules["handler"] = handler_mod

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
def recap_snippets():
    return sys.modules["recap.snippets"]


@pytest.fixture(scope="session")
def recap_generate():
    return sys.modules["recap.generate"]


@pytest.fixture(scope="session")
def recap_handler():
    return sys.modules["recap.handler"]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
