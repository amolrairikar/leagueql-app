import json
from typing import Any, Sequence

import aiohttp
import asyncio
import requests
from yarl import URL

from utils import logger, process_api_results

DATA_FETCH_TYPES = [
    "league_information",
    "settings",
    "draft_picks",
    "matchups",
    "player_scoring_totals",
]
V2_CUTOFF = 2018


class ESPNClient:
    """
    Class to set up ESPN API client for onboarding.

    Attributes:
        league_id: The ID of the league being onboarded.
        latest_season: Most recent season the league was active.
        espn_s2_cookie: Optional cookie value for espn_s2 cookie, required to fetch
            private ESPN league data.
        swid_cookie: Optional cookie value for SWID cookie, required to fetch
            private ESPN league data.

    Methods:
        __init__(league_id, latest_season, espn_s2_cookie, swid_cookie): Constructor
        get_league_seasons(latest_season): Gets list of all the seasons league has been active.
        _build_url(season, view): Constructs full ESPN Fantasy Football API url for a certain data view.
        _build_cookies(): Creates cookies object for espn_s2 and SWID cookies if needed.
        fetch_all(): Fetch all URLs at once asynchronously with a limit of 10 active calls.
        _fetch(): Fetch a single URL asynchronously.
        _structure_results(results): Groups API responses by season for simpler processing.
    """

    def __init__(self, league_id: str, latest_season: str, s2=None, swid=None):
        """Constructor."""
        if (
            bool(s2) ^ bool(swid)
        ):  # XOR operator: evaluates to True only if one is provided and the other isn't
            logger.error("Indicated private league, but missing one of swid or s2.")
            raise ValueError("Both swid and s2 must be defined if one is provided.")
        self.league_id = league_id
        self.s2 = s2
        self.swid = swid
        self.seasons = self._get_league_seasons(latest_season=latest_season)
        self.request_urls = self._build_all_request_urls()

    def _get_league_seasons(self, latest_season: str) -> list[str]:
        """
        Gets list of all the seasons league has been active.

        Args:
            latest_season: Most recent season the league was active.

        Returns:
            List of all seasons league has been active.
        """
        url = (
            f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
            f"/seasons/{latest_season}/segments/0/leagues/{self.league_id}?view=mTeam"
        )
        cookies = {}
        if self.s2:
            cookies["espn_s2"] = self.s2
        if self.swid:
            cookies["SWID"] = self.swid

        response = requests.get(url=url, cookies=cookies or None)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error("Error fetching active seasons for league: %s", e)
            raise e

        previous_seasons = response.json().get("status", {}).get("previousSeasons", [])
        previous_seasons = [str(season) for season in previous_seasons]
        return previous_seasons + [latest_season]

    def _construct_request_url(
        self, base_url: str, data_type: str, week: int | None = None
    ) -> str:
        """
        Creates full ESPN Fantasy Football API request URL based on the type of data to fetch.

        Args:
            base_url: The base URL for all API requests.
            data_type: The type of data to make an API request for.
            week: Optional, the week of the season to make an API request for.

        Returns:
            The full URL to make an API request to.
        """
        url = URL(base_url)
        param_map: dict[str, dict[str, list[str] | str]] = {
            "league_information": {"view": ["mTeam"]},
            "settings": {"view": ["mSettings", "mTeam"]},
            "draft_picks": {"view": ["mDraftDetail"]},
            "matchups": {"view": ["mBoxscore", "mMatchupScore"]},
            "player_scoring_totals": {"view": ["kona_player_info"]},
        }
        if data_type not in param_map:
            raise ValueError(f"Invalid data_type: {data_type}")
        params = param_map[data_type]
        if data_type == "matchups" and week:
            params["scoringPeriodId"] = str(week)
        return str(url.update_query(params))

    def _build_all_request_urls(self) -> list[tuple[str, str, str]]:
        """
        Constructs all ESPN Fantasy Football API request URLs needed to fetch data for app.

        Returns:
            List of tuples containing the season, data type, and request URL.
        """
        urls = []
        for season in self.seasons:
            for data_type in DATA_FETCH_TYPES:
                if int(season) <= V2_CUTOFF:
                    api_base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{self.league_id}?seasonId={season}"
                else:
                    api_base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{self.league_id}"
                if data_type == "matchups":
                    weeks = range(1, 19, 1) if int(season) >= 2021 else range(1, 18, 1)
                    for week in weeks:
                        full_url = self._construct_request_url(
                            base_url=api_base_url, data_type=data_type, week=week
                        )
                        urls.append((season, f"{data_type}_week{week}", full_url))
                else:
                    full_url = self._construct_request_url(
                        base_url=api_base_url, data_type=data_type
                    )
                    urls.append((season, data_type, full_url))
        return urls

    def _build_cookies(self) -> dict[str, str] | None:
        """
        Creates cookies object for espn_s2 and SWID cookies if needed.

        Returns:
            The cookies object for private leagues, else None.
        """
        # Cookies are only required to fetch private ESPN league data
        cookies = {}
        if self.s2:
            cookies["espn_s2"] = self.s2
        if self.swid:
            cookies["SWID"] = self.swid
        return cookies if cookies else None

    async def fetch_all(self) -> Sequence[dict[str, Any]]:
        """
        Fetch all URLs at once asynchronously with a limit of 10 active calls.

        Returns:
            All API request responses.
        """
        cookies = self._build_cookies()
        async with aiohttp.ClientSession(cookies=cookies) as session:
            semaphore = asyncio.Semaphore(10)
            tasks = [
                self._fetch(session=session, semaphore=semaphore, url_data=url_data)
                for url_data in self.request_urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return process_api_results(results=results)

    async def _fetch(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        url_data: tuple[str, str, str],
    ) -> dict[
        str, Any
    ]:  # NOTE: ESPN API response structure is too complex to type readably
        """
        Fetch a single URL asynchronously.

        Args:
            session: asyncio HTTP request session object.
            semaphore: Semaphore implementation which indicates the max number of async calls at once.
            url_data: Tuple of URL data containing the season, data type, and request URL.

        Returns:
            Mapping containing season, data type, and API response object.
        """
        season, data_type, url = url_data
        headers = {}
        if data_type == "player_scoring_totals":
            filter_val = {
                "players": {
                    "limit": 1500,
                    "sortAppliedStatTotal": {
                        "sortAsc": False,
                        "sortPriority": 2,
                        "value": "002024",
                    },
                }
            }
            headers["X-Fantasy-Filter"] = json.dumps(filter_val)
        async with semaphore:
            try:
                async with session.get(url=url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if isinstance(data, list):
                        data = data[0]

                    return {"season": season, "data_type": data_type, "data": data}
            except Exception as e:
                logger.error("Failed request for url: %s, error: %s", url, e)
                return {"season": season, "data_type": data_type, "data": None}
