import os
import uuid

import asyncio

from espn_client import ESPNClient
from sleeper_client import SleeperClient
from utils import logger
from writer import upload_results_to_s3, write_onboarding_status_to_dynamodb


class OnboardingService:
    """
    Class to handle onboarding process for league.

    Attributes:
        league_id: The ID of the league being onboarded.
        platform: The platform the league is on (e.g., ESPN, SLEEPER)
        request_type: The type of onboarding request (e.g., "ONBOARD" or "REFRESH")
        latest_season: Optional value for the most recent season a league was active,
            only required for ESPN leagues.
        espn_s2_cookie: Optional cookie value for espn_s2 cookie, required to fetch
            private ESPN league data.
        swid_cookie: Optional cookie value for SWID cookie, required to fetch
            private ESPN league data.
        canonical_league_id: The unique ID for the league, generated when initially onboarding a league. If none,
            the league has not been onboarded before. If provided, will be used to write raw refreshed data to the same
            S3 location as the original data and update the same DynamoDB metadata item as the original.

    Methods:
        __init__(league_id, platform, request_type, latest_season, espn_s2_cookie, swid_cookie, canonical_league_id): Constructor.
        run(): Runs the onboarding logic.
        _build_client(league_id, platform, latest_season, espn_s2_cookie, swid_cookie):
            Builds API request client for the provided platform (e.g., URL/cookie setup).
    """

    def __init__(
        self,
        league_id: str,
        platform: str,
        request_type: str,
        latest_season: str | None = None,
        espn_s2_cookie: str | None = None,
        swid_cookie: str | None = None,
        canonical_league_id: str | None = None,
        is_new_season_refresh: bool = False,
    ):
        """Constructor."""
        self.league_id = league_id
        self.platform = platform
        self.request_type = request_type
        self.is_new_season_refresh = is_new_season_refresh
        self.latest_season = str(latest_season) if latest_season else None
        self.client = self._build_client(
            league_id=league_id,
            platform=platform,
            latest_season=latest_season,
            espn_s2_cookie=espn_s2_cookie,
            swid_cookie=swid_cookie,
            is_refresh=(request_type == "REFRESH"),
        )
        self.canonical_league_id = canonical_league_id or str(uuid.uuid4())

    def run(self) -> None:
        """Runs the onboarding logic."""
        logger.info("Beginning raw data fetch")
        raw_data = asyncio.run(self.client.fetch_all())
        logger.info("Completed data fetch")
        logger.info("Updating job onboarding status in DynamoDB")
        if isinstance(self.client, ESPNClient):
            seasons = self.client.seasons
        else:
            seasons = list(self.client.season_mapping.keys())
        write_onboarding_status_to_dynamodb(
            league_id=self.league_id,
            platform=self.platform,
            canonical_league_id=self.canonical_league_id,
            seasons=seasons,
            request_type=self.request_type,
            is_new_season_refresh=self.is_new_season_refresh,
        )
        logger.info("Wrote job onboarding status to DynamoDB")
        logger.info("Writing raw data to S3")
        upload_results_to_s3(
            results=raw_data,
            bucket_name=os.environ["S3_BUCKET_NAME"],
            prefix=f"raw-api-data/{self.canonical_league_id}",
            platform=self.platform,
        )
        logger.info("Wrote raw data to S3")

    def _build_client(
        self,
        league_id: str,
        platform: str,
        latest_season: str | None = None,
        espn_s2_cookie: str | None = None,
        swid_cookie: str | None = None,
        is_refresh: bool = False,
    ) -> ESPNClient | SleeperClient:
        """
        Builds API request client for the provided platform (e.g., URL/cookie setup).

        Args:
            league_id: The ID of the league being onboarded.
            platform: The platform the league is on (e.g., ESPN, SLEEPER)
            latest_season: Optional value for the most recent season a league was active,
                only required for ESPN leagues.
            espn_s2_cookie: Optional cookie value for espn_s2 cookie, required to fetch
                private ESPN league data.
            swid_cookie: Optional cookie value for SWID cookie, required to fetch
                private ESPN league data.
            is_refresh: If True, only fetches the current season's data.

        Returns:
            ESPNClient or SleeperClient.
        """
        if platform == "ESPN":
            if not latest_season:
                raise ValueError("Latest season not provided for ESPN league.")
            return ESPNClient(
                league_id=league_id,
                latest_season=latest_season,
                s2=espn_s2_cookie,
                swid=swid_cookie,
                is_refresh=is_refresh,
            )
        elif platform == "SLEEPER":
            return SleeperClient(league_id, is_refresh=is_refresh)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
