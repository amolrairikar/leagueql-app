"""Tests for onboarder/handler.py."""

import json
from unittest.mock import MagicMock, patch

import requests


class TestLambdaHandlerMissingFields:
    def test_missing_body_returns_400(self, onboarder_handler):
        result = onboarder_handler.lambda_handler(
            {"requestType": "ONBOARD"}, MagicMock()
        )
        assert result["statusCode"] == 400
        assert "Missing required event field" in json.loads(result["body"])["error_msg"]

    def test_missing_request_type_returns_400(self, onboarder_handler):
        result = onboarder_handler.lambda_handler(
            {"body": {"leagueId": "123"}}, MagicMock()
        )
        assert result["statusCode"] == 400


class TestLambdaHandlerSleeperRefreshNoCanonicalId:
    def test_canonical_id_resolved_successfully(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        mock_svc = MagicMock()
        mock_svc.canonical_league_id = "canonical-abc"

        with (
            patch.object(
                onboarder_handler,
                "resolve_sleeper_canonical_league_id",
                return_value="canonical-abc",
            ),
            patch.object(
                onboarder_handler,
                "OnboardingService",
                return_value=mock_svc,
            ),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result["statusCode"] == 200

    def test_canonical_id_not_found_returns_404(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler,
            "resolve_sleeper_canonical_league_id",
            return_value=None,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 404

    def test_http_error_in_canonical_resolution_returns_502(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler,
            "resolve_sleeper_canonical_league_id",
            side_effect=requests.exceptions.HTTPError("err"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502

    def test_generic_error_in_canonical_resolution_returns_500(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler,
            "resolve_sleeper_canonical_league_id",
            side_effect=RuntimeError("unexpected"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 500


class TestLambdaHandlerServiceInitErrors:
    def test_key_error_in_init_returns_400(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler, "OnboardingService", side_effect=KeyError("leagueId")
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 400

    def test_value_error_in_init_returns_400(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "YAHOO"},
        }
        with patch.object(
            onboarder_handler,
            "OnboardingService",
            side_effect=ValueError("Unsupported platform"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 400

    def test_http_error_in_init_returns_502(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "ESPN", "season": "2024"},
        }
        with patch.object(
            onboarder_handler,
            "OnboardingService",
            side_effect=requests.exceptions.HTTPError("403"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502

    def test_runtime_error_in_init_returns_502(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler,
            "OnboardingService",
            side_effect=RuntimeError("API failure"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502


class TestLambdaHandlerRunErrors:
    def _make_service_mock(self, run_side_effect):
        svc = MagicMock()
        svc.canonical_league_id = "canonical-abc"
        svc.run.side_effect = run_side_effect
        return svc

    def test_key_error_during_run_returns_500(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = self._make_service_mock(KeyError("S3_BUCKET_NAME"))
        with patch.object(onboarder_handler, "OnboardingService", return_value=svc):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 500

    def test_runtime_error_during_run_returns_502(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = self._make_service_mock(RuntimeError("S3 error"))
        with patch.object(onboarder_handler, "OnboardingService", return_value=svc):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502

    def test_generic_exception_during_run_returns_500(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = self._make_service_mock(Exception("unexpected"))
        with patch.object(onboarder_handler, "OnboardingService", return_value=svc):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 500


class TestLambdaHandlerSuccess:
    def test_returns_200_with_canonical_id(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        mock_svc = MagicMock()
        mock_svc.canonical_league_id = "canonical-abc"
        mock_svc.run = MagicMock()

        with patch.object(
            onboarder_handler, "OnboardingService", return_value=mock_svc
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "succeeded"
        assert body["canonical_league_id"] == "canonical-abc"

    def test_espn_onboard_with_season(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {
                "leagueId": "456",
                "platform": "ESPN",
                "season": "2024",
                "s2": "abc",
                "swid": "{xyz}",
            },
        }
        mock_svc = MagicMock()
        mock_svc.canonical_league_id = "espn-id"
        mock_svc.run = MagicMock()

        with patch.object(
            onboarder_handler, "OnboardingService", return_value=mock_svc
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result["statusCode"] == 200

    def test_sleeper_refresh_with_existing_canonical_id(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "canonicalLeagueId": "existing-canonical",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        mock_svc = MagicMock()
        mock_svc.canonical_league_id = "existing-canonical"
        mock_svc.run = MagicMock()

        with patch.object(
            onboarder_handler, "OnboardingService", return_value=mock_svc
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result["statusCode"] == 200
