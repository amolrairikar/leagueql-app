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
    _nr_mock.agent.ASGIApplicationWrapper.side_effect = lambda app: app
    _nr_mock.agent.background_task.return_value = lambda f: f
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
        # Default: a stale stored matchup so refresh-guard tests are strictly
        # behind the default NFL state and proceed to the Lambda invoke. Tests
        # exercising the guard or other queries override this.
        mock.query.return_value = {"Items": [{"SK": "MATCHUPS#2024#WEEK#01"}]}
        yield mock


@pytest.fixture(autouse=True)
def default_nfl_state():
    """Stub Sleeper's NFL state to a 'behind' regular-season week so existing
    refresh tests still reach the Lambda invoke. Unit tests for get_nfl_state
    and the refresh guard reconfigure this mock as needed."""
    with patch("main.http_requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            **{
                "json.return_value": {
                    "season_type": "regular",
                    "season": "2025",
                    "week": "10",
                }
            }
        )
        yield mock_get


@pytest.fixture
def mock_lambda_client():
    with patch("main.lambda_client") as mock:
        yield mock


@pytest.fixture
def mock_s3_client():
    with patch("main.s3_client") as mock:
        yield mock


@pytest.fixture
def mock_time_sleep():
    """Patch the retry backoff sleep so delete tests run instantly."""
    with patch("helpers.time.sleep") as mock:
        yield mock


@pytest.fixture
def mock_sns_client():
    """Patch the shared SNS client as if SNS_TOPIC_ARN were configured."""
    with (
        patch("common.sns._sns_client") as mock,
        patch("common.sns._sns_topic_arn", "arn:aws:sns:us-east-1:123:test-topic"),
    ):
        yield mock


# Default Clerk user the auth dependency resolves to in unit tests. The shared
# league fixtures record this user as the league owner so owner-gated endpoints
# (LQL-01 / BE-016) succeed by default; tests for the 403 path override the auth
# dependency to a different user.
DEFAULT_TEST_USER = "user_1"


@pytest.fixture(autouse=True)
def override_authenticated_user():
    """Make endpoints see a fixed authenticated caller (LQL-01 / BE-016).

    Every league route now sits behind the Clerk JWT dependency; without an
    override the TestClient (which carries no JWT) would get 401. Tests that
    exercise the unauthenticated path pop this override explicitly.
    """
    import main
    import routes

    main.app.dependency_overrides[routes.get_authenticated_user] = lambda: (
        DEFAULT_TEST_USER
    )
    yield DEFAULT_TEST_USER
    main.app.dependency_overrides.pop(routes.get_authenticated_user, None)


@pytest.fixture
def client(aws_env_vars):
    import main

    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def league_lookup_item():
    # Harmless to lookup_league, which only reads canonical_league_id.
    # owner_user_id matches the default authed user so the owner gate passes when
    # this item doubles as METADATA.
    return {
        "PK": "LEAGUE#123#PLATFORM#SLEEPER",
        "SK": "LEAGUE_LOOKUP",
        "canonical_league_id": "canonical-abc",
        "seasons": {"2023", "2024"},
        "owner_user_id": DEFAULT_TEST_USER,
    }


@pytest.fixture
def league_metadata_item():
    # Status no longer lives on METADATA — it is tracked in the JOB_STATUS item.
    # By default there is no in-flight job (no active_job_id), so the concurrency
    # guard lets requests through; guard tests add active_job_id explicitly.
    # owner_user_id matches the default authed user so owner-gated endpoints
    # pass by default; 403 tests override the auth dependency to another user.
    return {
        "PK": "LEAGUE#canonical-abc",
        "SK": "METADATA",
        "league_name": "Test League",
        "owner_user_id": DEFAULT_TEST_USER,
        "members": {DEFAULT_TEST_USER},
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
