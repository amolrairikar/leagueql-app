import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def aws_env_vars():
    with patch.dict(
        os.environ,
        {"DYNAMODB_TABLE_NAME": "test-table", "S3_BUCKET_NAME": "test-bucket"},
    ):
        yield


@pytest.fixture
def mock_s3_client():
    with patch("handler.s3_client") as mock:
        yield mock


@pytest.fixture
def mock_table():
    with patch("handler.table") as mock:
        yield mock


@pytest.fixture
def mock_ddb_client():
    with patch("handler.ddb_client") as mock:
        yield mock
