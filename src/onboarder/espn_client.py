import json
from typing import Any, Sequence, Union

import aiohttp
import asyncio
import requests
from yarl import URL

from utils import logger

DATA_FETCH_TYPES = [
    "users",
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
        s2: Optional cookie value for espn_s2 cookie, required to fetch
            private ESPN league data.
        swid: Optional cookie value for SWID cookie, required to fetch
            private ESPN league data.
        is_refresh: Boolean indicating if this fetch is for a data refresh, which only fetches the latest season's data.

    Methods:
        __init__(league_id, latest_season, s2, swid, is_refresh): Constructor
        _get_league_seasons(latest_season): Gets list of all the seasons league has been active.
        _construct_request_url(base_url, data_type, week): Creates full ESPN Fantasy Football API request URL based on the type of data to fetch.
        _build_all_request_urls(): Constructs all ESPN Fantasy Football API request URLs needed to fetch data for app.
        _make_cookies_dict(): Builds the raw cookies dict from s2 and SWID values.
        _build_cookies(): Creates cookies object for espn_s2 and SWID cookies if needed.
        fetch_all(): Fetch all URLs at once asynchronously with a limit of 10 active calls.
        _fetch(session, semaphore, url_data): Fetch a single URL asynchronously.
    """

    def __init__(
        self,
        league_id: str,
        latest_season: str,
        s2: str | None = None,
        swid: str | None = None,
        is_refresh: bool = False,
    ):
        """Constructor."""
        if (
            bool(s2) ^ bool(swid)
        ):  # XOR operator: evaluates to True only if one is provided and the other isn't
            logger.error("Indicated private league, but missing one of swid or s2.")
            raise ValueError("Both swid and s2 must be defined if one is provided.")
        self.league_id = league_id
        self.s2 = s2
        self.swid = swid
        if is_refresh:
            self.seasons = [latest_season]
        else:
            self.seasons = self._get_league_seasons(latest_season=latest_season)
        self.request_urls = self._build_all_request_urls()

    def _get_league_seasons(self, latest_season: str) -> list[str]:
        """
        Gets list of all the seasons league has been active for prior to onboarding.

        Args:
            latest_season: Most recent season the league was active.

        Returns:
            List of all seasons league has been active.
        """
        url = (
            f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
            f"/seasons/{latest_season}/segments/0/leagues/{self.league_id}?view=mTeam"
        )
        cookies = self._make_cookies_dict()
        response = requests.get(url=url, cookies=cookies)
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
            "users": {"view": ["mTeam"]},
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

    def _make_cookies_dict(self) -> dict[str, str]:
        """Builds the raw cookies dict from s2 and SWID values."""
        cookies = {}
        if self.s2:
            cookies["espn_s2"] = self.s2
        if self.swid:
            cookies["SWID"] = self.swid
        return cookies

    def _build_cookies(self) -> dict[str, str] | None:
        """
        Creates cookies object for espn_s2 and SWID cookies if needed.

        Returns:
            The cookies object for private leagues, else None.
        """
        # Cookies are only required to fetch private ESPN league data
        cookies = self._make_cookies_dict()
        return cookies if cookies else None

    async def fetch_all(self) -> list[dict[str, Any]]:
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
            return self._process_api_results(results=results)

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
                        "value": f"00{season}",
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

    def _process_api_results(
        self,
        results: Sequence[Union[dict[str, Any], BaseException]],
    ) -> list[dict[str, Any]]:
        """
        Validates API responses and raises on any failure.

        Args:
            results: Unprocessed API responses.

        Returns:
            Validated API responses with no None data values.
        """
        processed_results = []
        for result in results:
            if isinstance(result, BaseException):
                logger.error("Unhandled exception in gather: %s", result)
                raise RuntimeError(
                    f"Unexpected error occurred while fetching data: {result}"
                )

            season: str = result["season"]
            data_type: str = result["data_type"]
            data = result["data"]

            if data is None:
                raise RuntimeError(
                    f"Failed to get data for season {season} and data type {data_type}"
                )

            # Filter ESPN responses due to large raw response size
            if data_type == "users":
                processed_data = {
                    "members": data["members"],
                    "teams": data["teams"],
                }
            elif data_type == "settings":
                processed_data = {
                    "settings": data["settings"],
                }
            elif data_type == "draft_picks":
                processed_data = {"draft_picks": data["draftDetail"]["picks"]}
            elif data_type.startswith("matchups"):
                matchup_week = data_type.removeprefix("matchups_week")
                matchups = data["schedule"]
                processed_matchups = [
                    matchup
                    for matchup in matchups
                    if str(matchup["matchupPeriodId"]) == str(matchup_week)
                ]
                processed_data = {"matchups": processed_matchups}
            elif data_type == "player_scoring_totals":
                processed_player_totals = []
                for player_total in data["players"]:
                    if int(season) <= V2_CUTOFF:
                        total_points = player_total.get("stats", [])[0].get(
                            "appliedTotal"
                        )
                    else:
                        total_points = (
                            player_total.get("ratings", {})
                            .get("0", {})
                            .get("totalRating")
                        )
                    processed_player_total = {
                        "player_id": player_total.get("player", {}).get("id"),
                        "player_name": player_total.get("player", {}).get("fullName"),
                        "position": player_total.get("player", {}).get(
                            "defaultPositionId"
                        ),
                        "total_points": total_points,
                    }
                    processed_player_totals.append(processed_player_total)
                processed_data = {"player_scoring_totals": processed_player_totals}
            else:
                raise ValueError(f"Invalid data_type: {data_type}")
            processed_result = {
                "season": season,
                "data_type": data_type,
                "data": processed_data,
            }

            processed_results.append(processed_result)

        return processed_results
