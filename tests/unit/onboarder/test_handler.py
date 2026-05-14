"""Tests for onboarder/handler.py."""

import json
from unittest.mock import MagicMock, patch

import requests


class TestLambdaHandler:
    def test_missing_body_returns_400(self, mock_context):
        from handler import lambda_handler

        result = lambda_handler({"requestType": "ONBOARD"}, mock_context)
        assert result["statusCode"] == 400

    def test_missing_request_type_returns_400(self, mock_context):
        from handler import lambda_handler

        result = lambda_handler({"body": {}}, mock_context)
        assert result["statusCode"] == 400

    def test_success_returns_200(self, mock_context):
        from handler import lambda_handler

        mock_service = MagicMock()
        mock_service.canonical_league_id = "canon-abc"
        mock_service.run = MagicMock()

        with patch("handler.OnboardingService", return_value=mock_service):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "SLEEPER"},
                    "requestType": "ONBOARD",
                },
                mock_context,
            )

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "succeeded"
        assert body["canonical_league_id"] == "canon-abc"

    def test_value_error_in_service_init_returns_400(self, mock_context):
        from handler import lambda_handler

        with patch("handler.OnboardingService", side_effect=ValueError("bad value")):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "ESPN"},
                    "requestType": "ONBOARD",
                },
                mock_context,
            )

        assert result["statusCode"] == 400

    def test_http_error_in_service_init_returns_502(self, mock_context):
        from handler import lambda_handler

        with patch(
            "handler.OnboardingService",
            side_effect=requests.exceptions.HTTPError("upstream fail"),
        ):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "ESPN", "season": "2024"},
                    "requestType": "ONBOARD",
                },
                mock_context,
            )

        assert result["statusCode"] == 502

    def test_runtime_error_in_run_returns_502(self, mock_context):
        from handler import lambda_handler

        mock_service = MagicMock()
        mock_service.run.side_effect = RuntimeError("upstream error")

        with patch("handler.OnboardingService", return_value=mock_service):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "SLEEPER"},
                    "requestType": "ONBOARD",
                },
                mock_context,
            )

        assert result["statusCode"] == 502

    def test_unexpected_error_in_run_returns_500(self, mock_context):
        from handler import lambda_handler

        mock_service = MagicMock()
        mock_service.run.side_effect = Exception("unexpected")

        with patch("handler.OnboardingService", return_value=mock_service):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "SLEEPER"},
                    "requestType": "ONBOARD",
                },
                mock_context,
            )

        assert result["statusCode"] == 500

    def test_sleeper_refresh_without_canonical_id_resolves_chain(self, mock_context):
        from handler import lambda_handler

        mock_service = MagicMock()
        mock_service.canonical_league_id = "canon-xyz"

        with (
            patch(
                "handler.resolve_sleeper_canonical_league_id", return_value="canon-xyz"
            ) as mock_resolve,
            patch("handler.OnboardingService", return_value=mock_service),
        ):
            result = lambda_handler(
                {
                    "body": {"leagueId": "new-123", "platform": "SLEEPER"},
                    "requestType": "REFRESH",
                },
                mock_context,
            )

        assert result["statusCode"] == 200
        mock_resolve.assert_called_once_with(new_league_id="new-123")

    def test_sleeper_refresh_canonical_not_found_returns_404(self, mock_context):
        from handler import lambda_handler

        with patch("handler.resolve_sleeper_canonical_league_id", return_value=None):
            result = lambda_handler(
                {
                    "body": {"leagueId": "unknown-123", "platform": "SLEEPER"},
                    "requestType": "REFRESH",
                },
                mock_context,
            )

        assert result["statusCode"] == 404

    def test_unexpected_error_resolving_canonical_id_returns_500(self, mock_context):
        from handler import lambda_handler

        with patch(
            "handler.resolve_sleeper_canonical_league_id",
            side_effect=Exception("totally unexpected"),
        ):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "SLEEPER"},
                    "requestType": "REFRESH",
                },
                mock_context,
            )

        assert result["statusCode"] == 500

    def test_key_error_in_service_init_returns_400(self, mock_context):
        from handler import lambda_handler

        result = lambda_handler(
            {"body": {"platform": "SLEEPER"}, "requestType": "ONBOARD"},
            mock_context,
        )
        assert result["statusCode"] == 400

    def test_runtime_error_in_service_init_returns_502(self, mock_context):
        from handler import lambda_handler

        with patch(
            "handler.OnboardingService", side_effect=RuntimeError("runtime error")
        ):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "ESPN", "season": "2024"},
                    "requestType": "ONBOARD",
                },
                mock_context,
            )

        assert result["statusCode"] == 502

    def test_key_error_in_run_returns_500(self, mock_context):
        from handler import lambda_handler

        mock_service = MagicMock()
        mock_service.run.side_effect = KeyError("S3_BUCKET_NAME")

        with patch("handler.OnboardingService", return_value=mock_service):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "SLEEPER"},
                    "requestType": "ONBOARD",
                },
                mock_context,
            )

        assert result["statusCode"] == 500

    def test_sleeper_refresh_http_error_resolving_id_returns_502(self, mock_context):
        from handler import lambda_handler

        with patch(
            "handler.resolve_sleeper_canonical_league_id",
            side_effect=requests.exceptions.HTTPError("fail"),
        ):
            result = lambda_handler(
                {
                    "body": {"leagueId": "123", "platform": "SLEEPER"},
                    "requestType": "REFRESH",
                },
                mock_context,
            )

        assert result["statusCode"] == 502
