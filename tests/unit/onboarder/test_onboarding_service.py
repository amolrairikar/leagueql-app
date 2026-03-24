import os
from unittest.mock import patch

import pytest

from onboarder.onboarding_service import OnboardingService


def make_espn_service(**kwargs):
    defaults = {"league_id": "123", "platform": "ESPN", "latest_season": "2023"}
    defaults.update(kwargs)
    with (
        patch("onboarder.onboarding_service.ESPNClient"),
        patch("onboarder.onboarding_service.SleeperClient"),
    ):
        return OnboardingService(**defaults)


class TestOnboardingServiceInit:
    def test_latest_season_converted_to_string_when_truthy(self):
        with patch("onboarder.onboarding_service.ESPNClient"):
            service = OnboardingService(
                league_id="123", platform="ESPN", latest_season=2023
            )
        assert service.latest_season == "2023"

    def test_latest_season_none_when_falsy(self):
        with patch("onboarder.onboarding_service.SleeperClient"):
            service = OnboardingService(
                league_id="123", platform="SLEEPER", latest_season=None
            )
        assert service.latest_season is None

    def test_stores_league_id_and_platform(self):
        with patch("onboarder.onboarding_service.ESPNClient"):
            service = OnboardingService(
                league_id="456", platform="ESPN", latest_season="2023"
            )
        assert service.league_id == "456"
        assert service.platform == "ESPN"


class TestBuildClient:
    def test_espn_platform_creates_espn_client(self):
        with patch("onboarder.onboarding_service.ESPNClient") as mock_espn_cls:
            service = OnboardingService(
                league_id="123",
                platform="ESPN",
                latest_season="2023",
                espn_s2_cookie="s2val",
                swid_cookie="{swid}",
            )

        mock_espn_cls.assert_called_once_with(
            league_id="123",
            latest_season="2023",
            s2="s2val",
            swid="{swid}",
        )
        assert service.client == mock_espn_cls.return_value

    def test_espn_platform_without_season_raises_value_error(self):
        with pytest.raises(ValueError, match="Latest season not provided"):
            OnboardingService(league_id="123", platform="ESPN", latest_season=None)

    def test_sleeper_platform_creates_sleeper_client(self):
        with patch("onboarder.onboarding_service.SleeperClient") as mock_sleeper_cls:
            service = OnboardingService(league_id="456", platform="SLEEPER")

        mock_sleeper_cls.assert_called_once_with("456")
        assert service.client == mock_sleeper_cls.return_value

    def test_unsupported_platform_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported platform: YAHOO"):
            OnboardingService(league_id="123", platform="YAHOO")


class TestRun:
    def test_run_fetches_and_uploads_to_s3(self):
        raw_data = [{"season": "2023", "data_type": "league_information", "data": {}}]

        with (
            patch("onboarder.onboarding_service.ESPNClient"),
            patch(
                "onboarder.onboarding_service.asyncio.run", return_value=raw_data
            ) as mock_run,
            patch("onboarder.onboarding_service.upload_results_to_s3") as mock_upload,
            patch(
                "onboarder.onboarding_service.write_onboarding_job_id_to_dynamodb",
                return_value="job-123",
            ) as mock_write_job,
            patch.dict(os.environ, {"S3_BUCKET_NAME": "test-bucket"}),
        ):
            service = OnboardingService(
                league_id="123", platform="ESPN", latest_season="2023"
            )
            result = service.run()

        mock_run.assert_called_once()
        mock_upload.assert_called_once_with(
            results=raw_data,
            bucket_name="test-bucket",
            key_name="raw-api-data/ESPN/123/onboard_job-123.json",
        )
        mock_write_job.assert_called_once()
        assert result == "job-123"
