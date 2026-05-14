import importlib.util
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

_SRC = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "../../../src/sleeper_player_stats_orchestrator"
    )
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
        {"S3_BUCKET_NAME": "test-bucket", "SQS_QUEUE_URL": "https://sqs.test/queue"},
    ):
        yield


@pytest.fixture(autouse=True)
def load_stats_orchestrator(aws_env_vars):
    for mod in ["utils", "handler"]:
        sys.modules.pop(mod, None)
    _load("utils", "utils.py")
    _load("handler", "handler.py")
    yield
    for mod in ["utils", "handler"]:
        sys.modules.pop(mod, None)


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.aws_request_id = "test-request-id"
    return ctx
