"""Tests for onboarder/onboarding_service.py."""

from unittest.mock import MagicMock, patch

import pytest
import requests


class TestOnboardingServiceInit:
    def test_espn_init_success(
        self, onboarder_onboarding_service, onboarder_espn_client
    ):
        with patch.object(
            onboarder_espn_client.ESPNClient,
            "_get_league_seasons",
            return_value=["2024"],
        ):
            svc = onboarder_onboarding_service.OnboardingService(
                league_id="123",
                platform="ESPN",
                request_type="ONBOARD",
                latest_season="2024",
            )
        assert svc.league_id == "123"
        assert svc.platform == "ESPN"
        assert svc.latest_season == "2024"

    def test_sleeper_init_success(
        self, onboarder_onboarding_service, onboarder_sleeper_client
    ):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "season": "2024",
            "league_id": "lg",
            "previous_league_id": "0",
        }
        with patch("requests.get", return_value=mock_resp):
            svc = onboarder_onboarding_service.OnboardingService(
                league_id="lg",
                platform="SLEEPER",
                request_type="ONBOARD",
            )
        assert svc.platform == "SLEEPER"

    def test_espn_missing_season_raises_value_error(self, onboarder_onboarding_service):
        with pytest.raises(ValueError, match="Latest season"):
            onboarder_onboarding_service.OnboardingService(
                league_id="123",
                platform="ESPN",
                request_type="ONBOARD",
            )

    def test_invalid_platform_raises_value_error(self, onboarder_onboarding_service):
        with pytest.raises(ValueError, match="Unsupported platform"):
            onboarder_onboarding_service.OnboardingService(
                league_id="123",
                platform="YAHOO",
                request_type="ONBOARD",
                latest_season="2024",
            )

    def test_canonical_league_id_generated_when_not_provided(
        self, onboarder_onboarding_service, onboarder_espn_client
    ):
        with patch.object(
            onboarder_espn_client.ESPNClient,
            "_get_league_seasons",
            return_value=["2024"],
        ):
            svc = onboarder_onboarding_service.OnboardingService(
                league_id="123",
                platform="ESPN",
                request_type="ONBOARD",
                latest_season="2024",
            )
        assert len(svc.canonical_league_id) == 36  # UUID length

    def test_canonical_league_id_used_when_provided(
        self, onboarder_onboarding_service, onboarder_espn_client
    ):
        with patch.object(
            onboarder_espn_client.ESPNClient,
            "_get_league_seasons",
            return_value=["2024"],
        ):
            svc = onboarder_onboarding_service.OnboardingService(
                league_id="123",
                platform="ESPN",
                request_type="REFRESH",
                latest_season="2024",
                canonical_league_id="existing-id",
            )
        assert svc.canonical_league_id == "existing-id"

    def test_is_refresh_passed_to_espn_client(self, onboarder_onboarding_service):
        svc = onboarder_onboarding_service.OnboardingService(
            league_id="123",
            platform="ESPN",
            request_type="REFRESH",
            latest_season="2024",
        )
        assert svc.client.seasons == ["2024"]

    def test_http_error_in_espn_client_init_propagates(
        self, onboarder_onboarding_service, onboarder_espn_client
    ):
        with patch.object(
            onboarder_espn_client.ESPNClient,
            "_get_league_seasons",
            side_effect=requests.exceptions.HTTPError("403"),
        ):
            with pytest.raises(requests.exceptions.HTTPError):
                onboarder_onboarding_service.OnboardingService(
                    league_id="123",
                    platform="ESPN",
                    request_type="ONBOARD",
                    latest_season="2024",
                )


class TestOnboardingServiceRun:
    def test_run_calls_fetch_upload_and_dynamodb(
        self,
        onboarder_onboarding_service,
        monkeypatch,
    ):
        monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"status": {"previousSeasons": []}}
        with patch("requests.get", return_value=mock_resp):
            svc = onboarder_onboarding_service.OnboardingService(
                league_id="123",
                platform="ESPN",
                request_type="ONBOARD",
                latest_season="2024",
            )

        mock_raw_data = [{"season": "2024", "data_type": "users", "data": {}}]

        async def fake_fetch():
            return mock_raw_data

        svc.client.fetch_all = fake_fetch

        with (
            patch.object(
                onboarder_onboarding_service, "write_onboarding_status_to_dynamodb"
            ) as mock_ddb,
            patch.object(
                onboarder_onboarding_service, "upload_results_to_s3"
            ) as mock_s3,
        ):
            svc.run()

        mock_ddb.assert_called_once()
        mock_s3.assert_called_once()
