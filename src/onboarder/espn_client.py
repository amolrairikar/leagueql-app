import asyncio
import json
from typing import Any, Sequence

import aiohttp
import requests
from yarl import URL

from utils import (
    V2_CUTOFF,
    fetch_with_retry,
    logger,
    matchup_weeks,
    run_fetches,
    validate_api_results,
)

DATA_FETCH_TYPES = [
    "users",
    "settings",
    "draft_picks",
    "matchups",
    "player_scoring_totals",
]
ESPN_PLAYER_FETCH_LIMIT = 1500


def _filter_users(
    data: dict[str, Any], _season: str, _data_type: str
) -> dict[str, Any]:
    return {"members": data["members"], "teams": data["teams"]}


def _filter_settings(
    data: dict[str, Any], _season: str, _data_type: str
) -> dict[str, Any]:
    return {"settings": data["settings"]}


def _filter_draft_picks(
    data: dict[str, Any], _season: str, _data_type: str
) -> dict[str, Any]:
    return {"draft_picks": data["draftDetail"]["picks"]}


def _filter_matchups(
    data: dict[str, Any], season: str, data_type: str
) -> dict[str, Any]:
    matchup_week = data_type.removeprefix("matchups_week")
    return {
        "matchups": [
            matchup
            for matchup in data["schedule"]
            if str(matchup["matchupPeriodId"]) == str(matchup_week)
        ]
    }


def _filter_player_scoring_totals(
    data: dict[str, Any], season: str, data_type: str
) -> dict[str, Any]:
    processed = []
    for player_total in data["players"]:
        if int(season) <= V2_CUTOFF:
            stats = player_total.get("player", {}).get("stats", [])
            total_points = stats[0].get("appliedTotal") if stats else None
        else:
            total_points = (
                player_total.get("ratings", {}).get("0", {}).get("totalRating")
            )
        processed.append(
            {
                "player_id": player_total.get("player", {}).get("id"),
                "player_name": player_total.get("player", {}).get("fullName"),
                "position": player_total.get("player", {}).get("defaultPositionId"),
                "total_points": total_points,
            }
        )
    return {"player_scoring_totals": processed}


_ESPN_DATA_FILTERS = {
    "users": _filter_users,
    "settings": _filter_settings,
    "draft_picks": _filter_draft_picks,
    "player_scoring_totals": _filter_player_scoring_totals,
}


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

    def get_seasons(self) -> list[str]:
        """Returns the list of seasons this league has been active."""
        return self.seasons

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
        response = requests.get(url=url, cookies=cookies, timeout=(5, 30))
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error("Error fetching active seasons for league: %s", e)
            raise e

        previous_seasons = response.json().get("status", {}).get("previousSeasons", [])
        previous_seasons = [str(season) for season in previous_seasons]
        all_seasons = previous_seasons + [latest_season]
        logger.info(
            "Resolved ESPN league seasons: league_id=%s season_count=%d seasons=%s",
            self.league_id,
            len(all_seasons),
            all_seasons,
        )
        return all_seasons

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
            season_int = int(season)
            for data_type in DATA_FETCH_TYPES:
                if season_int <= V2_CUTOFF:
                    api_base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{self.league_id}?seasonId={season}"
                else:
                    api_base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{self.league_id}"
                if data_type == "matchups":
                    weeks = matchup_weeks(season_int)
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
        logger.info(
            "Built ESPN request URLs: league_id=%s total_requests=%d",
            self.league_id,
            len(urls),
        )
        return urls

    def _make_cookies_dict(self) -> dict[str, str]:
        """Builds the raw cookies dict from s2 and SWID values."""
        cookies = {}
        if self.s2:
            cookies["espn_s2"] = self.s2
        if self.swid:
            cookies["SWID"] = self.swid
        return cookies

    async def fetch_all(self) -> list[dict[str, Any]]:
        """
        Fetch all URLs at once asynchronously with a limit of 10 active calls.

        Returns:
            All API request responses.
        """
        cookies = self._make_cookies_dict() or None
        async with aiohttp.ClientSession(
            cookies=cookies, timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            results = await run_fetches(session, self.request_urls, self._fetch)
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
                    "limit": ESPN_PLAYER_FETCH_LIMIT,
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
                data = await fetch_with_retry(session=session, url=url, headers=headers)
                logger.info("Successfully fetched url: %s", url)
                if isinstance(data, list):
                    data = data[0]
                return {"season": season, "data_type": data_type, "data": data}
            except Exception as e:
                logger.error("Failed request for url: %s, error: %s", url, e)
                return {"season": season, "data_type": data_type, "data": None}

    def _process_api_results(
        self,
        results: Sequence[dict[str, Any] | BaseException],
    ) -> list[dict[str, Any]]:
        """
        Validates API responses, filters ESPN-specific fields, and raises on any failure.

        Args:
            results: Unprocessed API responses.

        Returns:
            Validated and filtered API responses.
        """
        processed_results = []
        for result in validate_api_results(results):
            season: str = result["season"]
            data_type: str = result["data_type"]
            data = result["data"]

            if data_type.startswith("matchups"):
                filter_fn = _filter_matchups
            else:
                filter_fn = _ESPN_DATA_FILTERS.get(data_type)
                if filter_fn is None:
                    raise ValueError(f"Invalid data_type: {data_type}")

            processed_results.append(
                {
                    "season": season,
                    "data_type": data_type,
                    "data": filter_fn(data, season, data_type),
                }
            )

        return processed_results
