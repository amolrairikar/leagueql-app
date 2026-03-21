import asyncio

from espn_client import ESPNClient
from sleeper_client import SleeperClient
from transformer import Transformer
from utils import logger
from writer import DynamoWriter


class OnboardingService:
    """
    Class to handle onboarding process for league.

    Attributes:
        league_id: The ID of the league being onboarded.
        platform: The platform the league is on (e.g., ESPN, SLEEPER)
        latest_season: Optional value for the most recent season a league was active,
            only required for ESPN leagues.
        espn_s2_cookie: Optional cookie value for espn_s2 cookie, required to fetch
            private ESPN league data.
        swid_cookie: Optional cookie value for SWID cookie, required to fetch
            private ESPN league data.

    Methods:
        __init__(league_id, platform, latest_season, espn_s2_cookie, swid_cookie): Constructor.
        run(): Runs the onboarding logic.
        _build_client(league_id, platform, latest_season, espn_s2_cookie, swid_cookie):
            Builds API request client for the provided platform (e.g., URL/cookie setup).
    """

    def __init__(
        self,
        league_id: str,
        platform: str,
        latest_season: str | None = None,
        espn_s2_cookie: str | None = None,
        swid_cookie: str | None = None,
    ):
        """Constructor."""
        self.league_id = league_id
        self.platform = platform
        self.latest_season = str(latest_season) if latest_season else None
        self.client = self._build_client(
            league_id=league_id,
            platform=platform,
            latest_season=latest_season,
            espn_s2_cookie=espn_s2_cookie,
            swid_cookie=swid_cookie,
        )
        self.transformer = Transformer(platform=self.platform)
        self.writer = DynamoWriter(league_id=self.league_id, platform=self.platform)

    def run(self) -> None:
        """Runs the onboarding logic."""
        logger.info("Beginning raw data fetch")
        raw_data = asyncio.run(self.client.fetch_all())
        logger.info("Completed data fetch")
        logger.info("Beginning data transformation")
        views = self.transformer.transform(raw_data=raw_data)
        logger.info("Completed data transformation")
        logger.info("Beginning data write")
        self.writer.write_all(views=views)
        logger.info("Completed data write")

    def _build_client(
        self,
        league_id: str,
        platform: str,
        latest_season: str | None = None,
        espn_s2_cookie: str | None = None,
        swid_cookie: str | None = None,
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
            )
        elif platform == "SLEEPER":
            return SleeperClient(league_id)
        else:
            raise ValueError(f"Unsupported platform: {platform}")
