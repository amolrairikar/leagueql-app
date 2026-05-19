import asyncio
import os
from typing import Any

import aiohttp
import boto3
import botocore.exceptions
import requests

from utils import EXTENDED_SEASON_CUTOFF, fetch_with_retry, logger, validate_api_results

SLEEPER_BASE_URL = "https://api.sleeper.app/v1"
MAX_CHAIN_DEPTH = 50
_dynamodb = boto3.client("dynamodb")
DATA_FETCH_TYPES = [
    "users",
    "rosters",
    "matchups",
    "playoff_bracket",
    "losers_bracket",
    "transactions",
    "drafts",
    "league_settings",
]


def resolve_sleeper_canonical_league_id(new_league_id: str) -> str | None:
    """
    Resolves the canonical_league_id for a new Sleeper season by walking the
    previous_league_id chain until a known league ID is found in DynamoDB.

    Args:
        new_league_id: The new season's Sleeper league ID that is not yet in LEAGUE_LOOKUP.

    Returns:
        The canonical_league_id if a prior season is found in LEAGUE_LOOKUP, or None if
        the chain is exhausted without finding a match (truly unknown league).
    """
    table_name = os.environ["DYNAMODB_TABLE_NAME"]
    current_id = new_league_id
    depth = 0

    while True:
        if depth >= MAX_CHAIN_DEPTH:
            raise RuntimeError(
                f"Exceeded maximum chain depth of {MAX_CHAIN_DEPTH} while resolving canonical league ID for {new_league_id}"
            )
        depth += 1
        url = f"{SLEEPER_BASE_URL}/league/{current_id}"
        response = requests.get(url, timeout=(5, 30))
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(
                "Error fetching Sleeper league %s during chain walk: %s", current_id, e
            )
            raise

        data = response.json()
        previous_league_id = data.get("previous_league_id", "0")
        if previous_league_id == "0":
            logger.warning(
                "Exhausted previous_league_id chain from %s without finding a known league",
                new_league_id,
            )
            return None

        try:
            result = _dynamodb.get_item(
                TableName=table_name,
                Key={
                    "PK": {"S": f"LEAGUE#{previous_league_id}#PLATFORM#SLEEPER"},
                    "SK": {"S": "LEAGUE_LOOKUP"},
                },
            )
        except botocore.exceptions.ClientError as e:
            logger.error(
                "DynamoDB error while resolving Sleeper canonical league ID: %s", e
            )
            raise

        item = result.get("Item")
        if item and item.get("canonical_league_id"):
            canonical_league_id = item["canonical_league_id"]["S"]
            logger.info(
                "Resolved canonical_league_id %s for new season league ID %s via previous_league_id %s",
                canonical_league_id,
                new_league_id,
                previous_league_id,
            )
            return canonical_league_id

        current_id = previous_league_id


class SleeperClient:
    """
    Class to set up Sleeper API client for onboarding.

    Attributes:
        league_id: The ID of the most recent season's league being onboarded.

    Methods:
        __init__(league_id): Constructor.
        _get_league_seasons(): Gets mapping of all seasons the league has been active and the corresponding league_ids.
        _construct_request_url(league_id, data_type, week): Creates full Sleeper API request URL based on the type of data to fetch.
        _build_all_request_urls(): Constructs all Sleeper API request URLs needed to fetch data for app.
        fetch_all(): Fetch all URLs at once asynchronously with a limit of 10 active calls.
        _fetch(session, semaphore, url_data): Fetch a single URL asynchronously.
    """

    def __init__(self, league_id: str, is_refresh: bool = False):
        """Constructor."""
        self.league_id = league_id
        self.season_mapping = self._get_league_seasons(is_refresh=is_refresh)
        self.request_urls = self._build_all_request_urls()

    def _get_league_seasons(self, is_refresh: bool = False) -> dict[str, str]:
        """
        Gets mapping of all seasons the league has been active for prior to onboarding
        and the corresponding league_ids.

        Iteratively walks backwards through the league's history one season
        at a time via the previous_league_id field until it reaches the
        oldest season (previous_league_id == "0"), then returns the mapping.

        Args:
            is_refresh: If True, only fetches the current (most recent) season.

        Returns:
            Mapping of seasons league was active and the corresponding league_id for
                that season.
        """
        result: dict[str, str] = {}
        current_id = self.league_id
        depth = 0

        while True:
            if depth >= MAX_CHAIN_DEPTH:
                raise RuntimeError(
                    f"Exceeded maximum chain depth of {MAX_CHAIN_DEPTH} while fetching league seasons for {self.league_id}"
                )
            depth += 1
            url = f"{SLEEPER_BASE_URL}/league/{current_id}"
            response = requests.get(url, timeout=(5, 30))
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.error("Error fetching Sleeper league %s: %s", current_id, e)
                raise

            data = response.json()
            try:
                result[data["season"]] = data["league_id"]
            except KeyError as e:
                logger.error("Could not find league_id field in Sleeper API response")
                raise RuntimeError(
                    f"Unexpected response from Sleeper API: missing field {e}"
                ) from e

            if is_refresh:
                break

            previous_league_id = data.get("previous_league_id", "0")
            if previous_league_id == "0":
                break

            current_id = previous_league_id

        logger.info(
            "Resolved Sleeper league seasons: league_id=%s season_count=%d seasons=%s",
            self.league_id,
            len(result),
            list(result.keys()),
        )
        return result

    def get_seasons(self) -> list[str]:
        """Returns the list of seasons this league has been active."""
        return list(self.season_mapping.keys())

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
        elif data_type == "rosters":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/rosters"
        elif data_type == "matchups":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/matchups/{week}"
        elif data_type == "playoff_bracket":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/winners_bracket"
        elif data_type == "losers_bracket":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/losers_bracket"
        elif data_type == "transactions":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/transactions/{week}"
        elif data_type == "drafts":
            return f"{SLEEPER_BASE_URL}/league/{league_id}/drafts"
        elif data_type == "league_settings":
            return f"{SLEEPER_BASE_URL}/league/{league_id}"
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
                    weeks = (
                        range(1, 19)
                        if int(season) >= EXTENDED_SEASON_CUTOFF
                        else range(1, 18)
                    )
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
        logger.info(
            "Built Sleeper request URLs: league_id=%s total_requests=%d",
            self.league_id,
            len(urls),
        )
        return urls

    async def fetch_all(self) -> list[dict[str, Any]]:
        """
        Fetch all URLs at once asynchronously with a limit of 10 active calls.

        Returns:
            All API request responses.
        """
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            semaphore = asyncio.Semaphore(10)
            tasks = [
                self._fetch(session=session, semaphore=semaphore, url_data=url_data)
                for url_data in self.request_urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processed_results = validate_api_results(results=results)

            draft_pick_urls = self._build_draft_pick_urls(processed_results)
            if draft_pick_urls:
                pick_tasks = [
                    self._fetch(session=session, semaphore=semaphore, url_data=url_data)
                    for url_data in draft_pick_urls
                ]
                pick_results = await asyncio.gather(*pick_tasks, return_exceptions=True)
                processed_results.extend(validate_api_results(results=pick_results))

            return processed_results

    def _build_draft_pick_urls(
        self, results: list[dict[str, Any]]
    ) -> list[tuple[str, str, str]]:
        """
        Builds pick URLs from draft metadata results.

        Args:
            results: Processed API results containing draft metadata.

        Returns:
            List of tuples containing the season, data type, and pick URL for each draft.
        """
        urls = []
        for result in results:
            if result["data_type"] == "drafts":
                season = result["season"]
                drafts_data = result["data"]
                if isinstance(drafts_data, list):
                    for draft in drafts_data:
                        draft_id = draft.get("draft_id")
                        if draft_id:
                            url = f"{SLEEPER_BASE_URL}/draft/{draft_id}/picks"
                            urls.append((season, "draft_picks", url))
        logger.info(
            "Built Sleeper draft pick URLs: league_id=%s draft_count=%d",
            self.league_id,
            len(urls),
        )
        return urls

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
                data = await fetch_with_retry(session=session, url=url)
                return {"season": season, "data_type": data_type, "data": data}
            except Exception as e:
                logger.error("Failed request for url: %s, error: %s", url, e)
                return {"season": season, "data_type": data_type, "data": None}
