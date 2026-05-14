"""Tests for onboarder/onboarding_service.py."""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestOnboardingServiceBuildClient:
    def test_builds_sleeper_client(self):
        from onboarding_service import OnboardingService

        with patch("onboarding_service.SleeperClient") as mock_sleeper:
            mock_sleeper.return_value = MagicMock()
            service = OnboardingService(
                league_id="123",
                platform="SLEEPER",
                request_type="ONBOARD",
            )

        mock_sleeper.assert_called_once()
        assert service.platform == "SLEEPER"

    def test_builds_espn_client_with_season(self):
        from onboarding_service import OnboardingService

        with patch("onboarding_service.ESPNClient") as mock_espn:
            mock_espn.return_value = MagicMock()
            service = OnboardingService(
                league_id="123",
                platform="ESPN",
                request_type="ONBOARD",
                latest_season="2024",
            )

        mock_espn.assert_called_once()
        assert service.platform == "ESPN"
        assert service.latest_season == "2024"

    def test_espn_missing_season_raises_value_error(self):
        from onboarding_service import OnboardingService

        with pytest.raises(ValueError, match="Latest season not provided"):
            OnboardingService(
                league_id="123",
                platform="ESPN",
                request_type="ONBOARD",
            )

    def test_unsupported_platform_raises_value_error(self):
        from onboarding_service import OnboardingService

        with pytest.raises(ValueError, match="Unsupported platform"):
            OnboardingService(
                league_id="123",
                platform="YAHOO",
                request_type="ONBOARD",
            )

    def test_generates_uuid_when_no_canonical_id(self):
        from onboarding_service import OnboardingService

        with patch("onboarding_service.SleeperClient") as mock_sleeper:
            mock_sleeper.return_value = MagicMock()
            service = OnboardingService(
                league_id="123",
                platform="SLEEPER",
                request_type="ONBOARD",
            )

        assert service.canonical_league_id is not None
        assert len(service.canonical_league_id) == 36

    def test_uses_provided_canonical_league_id(self):
        from onboarding_service import OnboardingService

        with patch("onboarding_service.SleeperClient") as mock_sleeper:
            mock_sleeper.return_value = MagicMock()
            service = OnboardingService(
                league_id="123",
                platform="SLEEPER",
                request_type="REFRESH",
                canonical_league_id="canon-xyz",
            )

        assert service.canonical_league_id == "canon-xyz"

    def test_sleeper_refresh_passes_is_refresh_true(self):
        from onboarding_service import OnboardingService

        with patch("onboarding_service.SleeperClient") as mock_sleeper:
            mock_sleeper.return_value = MagicMock()
            OnboardingService(
                league_id="123",
                platform="SLEEPER",
                request_type="REFRESH",
                canonical_league_id="canon-xyz",
            )

        call_kwargs = mock_sleeper.call_args[1]
        assert call_kwargs.get("is_refresh") is True


class TestOnboardingServiceRun:
    def test_run_fetches_data_and_writes_to_s3(self):
        from onboarding_service import OnboardingService

        mock_client = MagicMock()
        mock_client.get_seasons.return_value = ["2024"]

        with (
            patch("onboarding_service.SleeperClient", return_value=mock_client),
            patch("onboarding_service.write_onboarding_status_to_dynamodb") as mock_ddb,
            patch("onboarding_service.upload_results_to_s3") as mock_upload,
            patch("onboarding_service.asyncio.run", return_value=[]) as mock_run,
            patch.dict(os.environ, {"S3_BUCKET_NAME": "test-bucket"}),
        ):
            service = OnboardingService(
                league_id="123",
                platform="SLEEPER",
                request_type="ONBOARD",
            )
            service.run()

        mock_run.assert_called_once()
        mock_ddb.assert_called_once_with(
            league_id="123",
            platform="SLEEPER",
            canonical_league_id=service.canonical_league_id,
            seasons=["2024"],
            request_type="ONBOARD",
            is_new_season_refresh=False,
        )
        mock_upload.assert_called_once()
