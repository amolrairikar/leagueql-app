from typing import Any, Sequence

import aiohttp
import asyncio
import requests

from utils import logger, process_api_results

SLEEPER_BASE_URL = "https://api.sleeper.app/v1"
DATA_FETCH_TYPES = [
    "users",
    "matchups",
    "playoff_bracket",
    "transactions",
    "drafts",
]


class SleeperClient:
    """
    Class to set up Sleeper API client for onboarding.

    Attributes:
        league_id: The ID of the most recent season's league being onboarded.

    Methods:
        __init__(league_id): Constructor.
        get_league_seasons(): Gets list of all seasons the league has been active using
            an exponential jump + binary search algorithm to efficiently find the oldest season
            without iterating one by one.
    """

    def __init__(self, league_id: str):
        """Constructor."""
        self.league_id = league_id
        self.season_mapping = self._get_league_seasons()
        self.request_urls = self._build_all_request_urls()

    def _get_league_seasons(self) -> dict[str, str]:
        """
        Gets mapping of all seasons the league has been active and the corresponding
        league_ids.

        Iteratively walks backwards through the league's history one season
        at a time via the previous_league_id field until it reaches the
        oldest season (previous_league_id == "0"), then returns the mapping.

        Returns:
            Mapping of seasons league was active and the corresponding league_id for
                that season.
        """
        result: dict[str, str] = {}
        current_id = self.league_id

        while True:
            url = f"{SLEEPER_BASE_URL}/league/{current_id}"
            response = requests.get(url)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.error("Error fetching Sleeper league %s: %s", current_id, e)
                raise e

            data = response.json()
            result[data["season"]] = data["league_id"]
            previous_league_id = data.get("previous_league_id", "0")
            if previous_league_id == "0":
                break

            current_id = previous_league_id

        return result

    def _construct_request_url(
        self, league_id: str, data_type: str, week: int | None = None
    ) -> str:
        """
        Creates full Sleeper API request URL based on the type of data to fetch.

        Args:
            league_id: The ID corresponding to the league we are fetching data for.
            data_type: The type of data to make an API request for.
            week: Optional, the week of the season to make an API request for.

        Returns:
            The full URL to make an API request to.
        """
        if data_type == "users":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/users"
        elif data_type == "matchups":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/matchups/{week}"
        elif data_type == "playoff_bracket":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/winners_bracket"
        elif data_type == "transactions":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/transactions/{week}"
        elif data_type == "drafts":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/drafts"
        raise ValueError(
            f"Invalid data_type: {data_type}, or week not provided for matchups or transactions."
        )

    def _build_all_request_urls(self) -> list[tuple[str, str, str]]:
        """
        Constructs all Sleeper API request URLs needed to fetch data for app.

        Returns:
            List of tuples containing the season, data type, and request URL.
        """
        urls = []
        for season, league_id in self.season_mapping.items():
            for data_type in DATA_FETCH_TYPES:
                if data_type in ("matchups", "transactions"):
                    weeks = range(1, 19, 1) if int(season) >= 2021 else range(1, 18, 1)
                    for week in weeks:
                        full_url = self._construct_request_url(
                            league_id=league_id, data_type=data_type, week=week
                        )
                        urls.append((season, f"{data_type}_week{week}", full_url))
                else:
                    full_url = self._construct_request_url(
                        league_id=league_id, data_type=data_type
                    )
                    urls.append((season, data_type, full_url))
        return urls

    async def fetch_all(self) -> Sequence[dict[str, Any]]:
        """
        Fetch all URLs at once asynchronously with a limit of 10 active calls.

        Returns:
            All API request responses.
        """
        async with aiohttp.ClientSession() as session:
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
    ]:  # NOTE: Sleeper API response structure is too complex to type readably
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
        async with semaphore:
            try:
                async with session.get(url=url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return {"season": season, "data_type": data_type, "data": data}
            except Exception as e:
                logger.error("Failed request for url: %s, error: %s", url, e)
                return {"season": season, "data_type": data_type, "data": None}
