import importlib.util
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../src/onboarder")
)


def _load(name, rel_path):
    path = os.path.join(_SRC, rel_path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def aws_env_vars():
    with patch.dict(
        os.environ,
        {"DYNAMODB_TABLE_NAME": "test-table", "S3_BUCKET_NAME": "test-bucket"},
    ):
        yield


@pytest.fixture(autouse=True)
def load_onboarder_handler(aws_env_vars):
    sys.modules.pop("handler", None)
    _load("handler", "handler.py")
    yield
    sys.modules.pop("handler", None)


@pytest.fixture
def mock_s3():
    with patch("writer._s3") as mock:
        yield mock


@pytest.fixture
def mock_dynamodb():
    with patch("writer._dynamodb") as mock:
        yield mock


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.aws_request_id = "test-request-id"
    ctx.function_name = "test-function"
    return ctx
