import json
from unittest.mock import MagicMock, patch

import requests

from onboarder.handler import lambda_handler


def make_event(body=None):
    if body is None:
        body = {
            "leagueId": 123,
            "platform": "espn",
            "season": "2023",
            "s2": "abc",
            "swid": "{guid}",
        }
    return {"body": body}


class TestLambdaHandlerSuccess:
    def test_returns_200_on_success(self):
        context = MagicMock()
        mock_service = MagicMock()
        mock_service.run.return_value = "job-123"

        with patch("onboarder.handler.OnboardingService", return_value=mock_service):
            result = lambda_handler(make_event(), context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "succeeded"
        assert body["onboarding_job_id"] == "job-123"
        mock_service.run.assert_called_once()

    def test_optional_fields_passed_as_none(self):
        context = MagicMock()
        event = make_event({"leagueId": 456, "platform": "espn"})
        mock_service = MagicMock()
        mock_service.run.return_value = "job-456"

        with patch(
            "onboarder.handler.OnboardingService", return_value=mock_service
        ) as mock_cls:
            result = lambda_handler(event, context)

        assert result["statusCode"] == 200
        _, kwargs = mock_cls.call_args
        assert kwargs["latest_season"] is None
        assert kwargs["espn_s2_cookie"] is None
        assert kwargs["swid_cookie"] is None


class TestLambdaHandlerOnboardingServiceErrors:
    def test_key_error_returns_400(self):
        context = MagicMock()
        event = make_event({"platform": "espn"})  # missing leagueId

        with patch(
            "onboarder.handler.OnboardingService", side_effect=KeyError("leagueId")
        ):
            result = lambda_handler(event, context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["status"] == "failed"
        assert "leagueId" in body["error_msg"]

    def test_value_error_returns_400(self):
        context = MagicMock()

        with patch(
            "onboarder.handler.OnboardingService",
            side_effect=ValueError("invalid platform"),
        ):
            result = lambda_handler(make_event(), context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["status"] == "failed"
        assert "invalid platform" in body["error_msg"]

    def test_http_error_returns_502(self):
        context = MagicMock()

        with patch(
            "onboarder.handler.OnboardingService",
            side_effect=requests.exceptions.HTTPError("503 Service Unavailable"),
        ):
            result = lambda_handler(make_event(), context)

        assert result["statusCode"] == 502
        body = json.loads(result["body"])
        assert body["status"] == "failed"

    def test_runtime_error_returns_502(self):
        context = MagicMock()

        with patch(
            "onboarder.handler.OnboardingService",
            side_effect=RuntimeError("fetch failed"),
        ):
            result = lambda_handler(make_event(), context)

        assert result["statusCode"] == 502
        body = json.loads(result["body"])
        assert body["status"] == "failed"
        assert "fetch failed" in body["error_msg"]


class TestLambdaHandlerRunErrors:
    def test_key_error_in_run_returns_400(self):
        context = MagicMock()
        mock_service = MagicMock()
        mock_service.run.side_effect = KeyError("DYNAMODB_TABLE_NAME")

        with patch("onboarder.handler.OnboardingService", return_value=mock_service):
            result = lambda_handler(make_event(), context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["status"] == "failed"
        assert "DYNAMODB_TABLE_NAME" in body["error_msg"]

    def test_runtime_error_in_run_returns_502(self):
        context = MagicMock()
        mock_service = MagicMock()
        mock_service.run.side_effect = RuntimeError("processing failed")

        with patch("onboarder.handler.OnboardingService", return_value=mock_service):
            result = lambda_handler(make_event(), context)

        assert result["statusCode"] == 502
        body = json.loads(result["body"])
        assert body["status"] == "failed"
        assert "processing failed" in body["error_msg"]

    def test_unexpected_exception_in_run_returns_500(self):
        context = MagicMock()
        mock_service = MagicMock()
        mock_service.run.side_effect = Exception("unexpected error")

        with patch("onboarder.handler.OnboardingService", return_value=mock_service):
            result = lambda_handler(make_event(), context)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "failed"
        assert "unexpected error" in body["error_msg"]
