import asyncio
import os
import uuid

from espn_client import ESPNClient
from sleeper_client import SleeperClient
from utils import logger
from writer import (
    read_failed_lineup_seasons,
    send_lineup_backfill_message,
    upload_results_to_s3,
    write_league_records,
)
from yahoo_client import YahooClient


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
        reprocess_all: When True, tags the manifest so the processor rebuilds every
            season's views (used by the backend/sleeper-transactions backfill); default False.
        refetch_all: When True on a REFRESH, the platform client resolves the league's full
            season history instead of only the latest season, so every season's raw data is
            re-fetched (backend/league-refresh backfill); default False.

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
        owner_user_id: str | None = None,
        reprocess_all: bool = False,
        auto_refresh: bool | None = None,
        refetch_all: bool = False,
    ):
        """Constructor."""
        self.league_id = league_id
        self.platform = platform
        self.request_type = request_type
        self.is_new_season_refresh = is_new_season_refresh
        self.owner_user_id = owner_user_id
        self.reprocess_all = reprocess_all
        self.refetch_all = refetch_all
        # Per-league scheduled auto-refresh opt-in (backend/scheduled-league-auto-refresh).
        # None means "not specified" (e.g. a scheduled refresh) — the flag is left untouched;
        # a bool is an explicit user choice written onto METADATA.
        self.auto_refresh = auto_refresh
        self.latest_season = str(latest_season) if latest_season else None
        self.client = self._build_client(
            league_id=league_id,
            platform=platform,
            latest_season=latest_season,
            espn_s2_cookie=espn_s2_cookie,
            swid_cookie=swid_cookie,
            owner_user_id=owner_user_id,
            # A refetch-all REFRESH keeps the REFRESH write path but fetches every season.
            is_refresh=(request_type in ("REFRESH", "MIGRATE")) and not refetch_all,
        )
        self.canonical_league_id = canonical_league_id or str(uuid.uuid4())

    def run(self) -> None:
        """Runs the onboarding logic."""
        seasons = self.client.get_seasons()
        logger.info(
            "Beginning raw data fetch: platform=%s seasons=%s season_count=%d",
            self.platform,
            seasons,
            len(seasons),
        )
        raw_data = asyncio.run(self.client.fetch_all())
        logger.info("Completed raw data fetch: records_fetched=%d", len(raw_data))
        # Record only the seasons that actually onboarded. fetch_all drops any season with
        # a failed API call (backend/league-onboarding: "Onboard seasons resiliently"), so
        # a skipped season must not appear in the recorded ``seasons`` set — deriving it
        # from the fetched data keeps METADATA/LEAGUE_LOOKUP consistent with the S3 files
        # written by upload_results_to_s3 (which also groups by the seasons in raw_data).
        onboarded_seasons = sorted({str(record["season"]) for record in raw_data})
        lineup_pending_seasons = self._lineup_pending_seasons(onboarded_seasons)
        logger.info("Updating job onboarding status in DynamoDB")
        write_league_records(
            league_id=self.league_id,
            platform=self.platform,
            canonical_league_id=self.canonical_league_id,
            seasons=onboarded_seasons,
            request_type=self.request_type,
            is_new_season_refresh=self.is_new_season_refresh,
            owner_user_id=self.owner_user_id,
            auto_refresh=self.auto_refresh,
            lineup_pending_seasons=lineup_pending_seasons,
        )
        logger.info("Wrote job onboarding status to DynamoDB")
        logger.info(
            "Writing raw data to S3: canonical_league_id=%s season_count=%d",
            self.canonical_league_id,
            len(onboarded_seasons),
        )
        upload_results_to_s3(
            results=raw_data,
            bucket_name=os.environ["S3_BUCKET_NAME"],
            prefix=f"raw-api-data/{self.canonical_league_id}",
            platform=self.platform,
            reprocess_all=self.reprocess_all,
        )
        logger.info("Wrote raw data to S3")
        if lineup_pending_seasons:
            self._queue_lineup_backfill()

    def _lineup_pending_seasons(self, onboarded_seasons: list[str]) -> list[str]:
        """Seasons the Yahoo lineup backfill must fill in (backend/yahoo-lineup-backfill).

        Yahoo onboards/refreshes no longer fetch per-team weekly rosters, so every onboarded
        season becomes lineup-pending. A REFRESH also re-queues seasons whose backfill
        previously exhausted its retries. Other platforms fetch lineups inline: none.
        """
        if self.platform != "YAHOO":
            return []
        seasons = set(onboarded_seasons)
        if self.request_type == "REFRESH":
            seasons |= set(read_failed_lineup_seasons(self.canonical_league_id))
        return sorted(seasons)

    def _queue_lineup_backfill(self) -> None:
        """Queue the league's lineup backfill; best-effort (a later refresh re-queues)."""
        try:
            send_lineup_backfill_message(self.canonical_league_id)
            logger.info(
                "Queued lineup backfill: canonical_league_id=%s",
                self.canonical_league_id,
            )
        except Exception as e:  # noqa: BLE001 — the onboard itself already succeeded
            logger.error(
                "Failed to queue lineup backfill for %s: %s",
                self.canonical_league_id,
                e,
            )

    def _build_client(
        self,
        league_id: str,
        platform: str,
        latest_season: str | None = None,
        espn_s2_cookie: str | None = None,
        swid_cookie: str | None = None,
        owner_user_id: str | None = None,
        is_refresh: bool = False,
    ) -> ESPNClient | SleeperClient | YahooClient:
        """
        Builds API request client for the provided platform (e.g., URL/cookie setup).

        Args:
            league_id: The ID of the league being onboarded.
            platform: The platform the league is on (e.g., ESPN, SLEEPER, YAHOO)
            latest_season: Optional value for the most recent season a league was active,
                only required for ESPN leagues.
            espn_s2_cookie: Optional cookie value for espn_s2 cookie, required to fetch
                private ESPN league data.
            swid_cookie: Optional cookie value for SWID cookie, required to fetch
                private ESPN league data.
            owner_user_id: The onboarding owner's Clerk user id, whose linked Yahoo token
                authorizes Yahoo fetches (required for YAHOO).
            is_refresh: If True, only fetches the current season's data.

        Returns:
            ESPNClient, SleeperClient, or YahooClient.
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
        elif platform == "YAHOO":
            if not owner_user_id:
                raise ValueError("Owner user id not provided for Yahoo league.")
            return YahooClient(
                league_id=league_id,
                owner_user_id=owner_user_id,
                is_refresh=is_refresh,
            )
        else:
            raise ValueError(f"Unsupported platform: {platform}")
