import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_main():
    """Import main once with boto3 mocked to prevent real AWS calls at module load time."""
    _nr_mock = MagicMock()
    _nr_mock.agent.lambda_handler.return_value = lambda f: f
    sys.modules.setdefault("newrelic", _nr_mock)
    sys.modules.setdefault("newrelic.agent", _nr_mock.agent)

    with patch.dict(
        os.environ,
        {
            "DYNAMODB_TABLE_NAME": "test-table",
            "S3_BUCKET_NAME": "test-bucket",
            "ONBOARDER_LAMBDA_NAME": "test-onboarder",
        },
    ):
        with (
            patch("boto3.resource") as mock_resource,
            patch("boto3.client") as mock_client,
        ):
            mock_resource.return_value.Table.return_value = MagicMock()
            mock_client.return_value = MagicMock()
            import main  # noqa: F401


@pytest.fixture(autouse=True)
def aws_env_vars():
    with patch.dict(
        os.environ,
        {
            "DYNAMODB_TABLE_NAME": "test-table",
            "S3_BUCKET_NAME": "test-bucket",
            "ONBOARDER_LAMBDA_NAME": "test-onboarder",
        },
    ):
        yield


@pytest.fixture
def mock_table():
    with patch("main.table") as mock:
        yield mock


@pytest.fixture
def mock_lambda_client():
    with patch("main.lambda_client") as mock:
        yield mock


@pytest.fixture
def mock_s3_client():
    with patch("main.s3_client") as mock:
        yield mock


@pytest.fixture
def client(aws_env_vars):
    import main

    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def league_lookup_item():
    return {
        "PK": "LEAGUE#123#PLATFORM#SLEEPER",
        "SK": "LEAGUE_LOOKUP",
        "canonical_league_id": "canonical-abc",
        "seasons": {"2023", "2024"},
    }


@pytest.fixture
def league_metadata_item():
    return {
        "PK": "LEAGUE#canonical-abc",
        "SK": "METADATA",
        "league_name": "Test League",
        "onboarding_status": "COMPLETED",
        "refresh_status": "COMPLETED",
    }


@pytest.fixture
def sample_matchup_items():
    return [
        {
            "PK": "LEAGUE#canonical-abc",
            "SK": "MATCHUPS#2024",
            "data": [
                {
                    "week": 1,
                    "home_score": Decimal("120.5"),
                    "away_score": Decimal("98.3"),
                },
            ],
        }
    ]
