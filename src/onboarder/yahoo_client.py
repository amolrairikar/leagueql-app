"""Yahoo Fantasy Football onboarding client (backend/league-onboarding).

Mirrors the ESPN/Sleeper client contract (``get_seasons`` + ``async fetch_all`` returning
``{"season","data_type","data"}`` records) for Yahoo leagues. Yahoo differs in two ways:

* **Auth** is a Bearer access token for the linked *owner* (resolved/refreshed through
  ``common.yahoo_tokens``), not ESPN cookies.
* **Addressing** — a league is ``{game_key}.l.{league_id}`` and Yahoo mints a new numeric
  ``league_id`` each season, linking seasons via a ``renew`` pointer. ``get_seasons`` enumerates
  the owner's NFL leagues (which also verifies membership), resolves the entered numeric id to its
  ``league_key``, and walks the ``renew`` chain to assemble the full history.

Yahoo's ``?format=json`` uses deeply nested, numeric-keyed containers; the parsing helpers here
(``_flatten``, ``_collection_items``) normalize those into plain dicts/lists, and the per-type
filter functions produce the grouped shapes the processor's ``_register_yahoo_raw_data`` consumes.
Player season scoring/names are **not** fetched here — they come from the separate Yahoo
player-data cache in S3 (see ``yahoo_player_stats_refresher``); records here carry player *keys*.
"""

import asyncio
from collections.abc import Callable, Sequence
from typing import Any

import aiohttp
import requests
from utils import (
    describe_fetch_error,
    fetch_with_retry,
    logger,
    run_fetches,
    validate_api_results,
)

# The pure Yahoo JSON-normalization helpers live in a shared module so the API Lambda's
# Yahoo-members proxy can reuse them without importing this onboarding client.
from common.yahoo_members import (
    _collection_items,
    _flatten,
    _league_subresource,
    _primary_manager,
    resolve_team_owner_ids,
)

YAHOO_BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"

# Per-league sub-resources fetched once per season (matchups are expanded per week separately).
DATA_FETCH_TYPES = [
    "settings",
    "standings",
    "teams",
    "draft_picks",
    "transactions",
]

# Yahoo returns 25 collection items per page; transactions/players page with ``start=``.
YAHOO_PAGE_SIZE = 25

# Keep Yahoo fan-out gentler than ESPN/Sleeper — Yahoo throttles aggressively.
YAHOO_CONCURRENCY = 4


# --------------------------------------------------------------------------------------
# Yahoo JSON normalization helpers: ``_flatten`` / ``_collection_items`` / ``_league_subresource``
# are imported from ``common.yahoo_members`` (shared with the API Lambda's members proxy).
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# Per-type filters: normalize a raw Yahoo payload into the grouped shape the processor wants
# --------------------------------------------------------------------------------------
def _filter_settings(data: dict[str, Any], _season: str, _dt: str) -> dict[str, Any]:
    league = data.get("fantasy_content", {}).get("league", [])
    meta = _flatten(league[0]) if isinstance(league, list) and league else {}
    settings_node = _league_subresource(data, "settings")
    settings = _flatten(settings_node[0]) if isinstance(settings_node, list) else {}
    return {
        "name": meta.get("name"),
        "num_playoff_teams": settings.get("num_playoff_teams"),
        "playoff_start_week": settings.get("playoff_start_week"),
    }


def _filter_standings(data: dict[str, Any], _season: str, _dt: str) -> dict[str, Any]:
    standings_node = _league_subresource(data, "standings")
    node = standings_node[0] if isinstance(standings_node, list) else standings_node
    teams = _collection_items((node or {}).get("teams", {}), "team")
    rows = []
    for team in teams:
        flat = _flatten(team)
        team_standings = _flatten(flat.get("team_standings", {}))
        rows.append(
            {
                "team_key": flat.get("team_key"),
                "rank": team_standings.get("rank"),
            }
        )
    return {"standings": rows}


def _filter_teams(data: dict[str, Any], _season: str, _dt: str) -> dict[str, Any]:
    teams = _collection_items(_league_subresource(data, "teams") or {}, "team")
    flats = [_flatten(team) for team in teams]
    owner_ids = resolve_team_owner_ids(flats)
    members, out_teams = [], []
    for flat, owner_id in zip(flats, owner_ids):
        primary = _primary_manager(flat)
        logos = _collection_items(flat.get("team_logos", {}), "team_logo")
        logo_url = _flatten(logos[0]).get("url") if logos else None
        members.append(
            {
                "manager_id": owner_id,
                "nickname": primary.get("nickname"),
            }
        )
        out_teams.append(
            {
                "team_key": flat.get("team_key"),
                "team_id": flat.get("team_id"),
                "name": flat.get("name"),
                "logo": logo_url,
                "manager_id": owner_id,
            }
        )
    return {"members": members, "teams": out_teams}


def _filter_matchups(
    data: dict[str, Any], _season: str, data_type: str
) -> dict[str, Any]:
    week = data_type.removeprefix("matchups_week")
    scoreboard = _league_subresource(data, "scoreboard")
    node = scoreboard[0] if isinstance(scoreboard, list) else scoreboard
    # Yahoo nests matchups one level deeper: {"0": {"matchups": {...}}, "week": W}.
    inner = _flatten((node or {}).get("0", {})) or (node or {})
    matchups = _collection_items(inner.get("matchups", {}), "matchup")
    rows = []
    for matchup in matchups:
        flat = _flatten(matchup)
        teams = _collection_items(_flatten(flat.get("0", {})).get("teams", {}), "team")
        parsed = []
        for team in teams:
            tflat = _flatten(team)
            points = _flatten(tflat.get("team_points", {}))
            parsed.append(
                {
                    "team_key": tflat.get("team_key"),
                    "points": points.get("total"),
                }
            )
        rows.append(
            {
                "week": week,
                "is_playoffs": flat.get("is_playoffs"),
                "is_consolation": flat.get("is_consolation"),
                "winner_team_key": flat.get("winner_team_key"),
                "teams": parsed,
            }
        )
    return {"matchups": rows}


def _filter_rosters(
    data: dict[str, Any], _season: str, data_type: str
) -> dict[str, Any]:
    """Flatten a weekly ``teams/roster/players/stats`` payload into per-player roster rows.

    One call per week returns every team's roster with each player's ``selected_position`` and
    weekly ``player_points``; the processor joins these to matchups to build starter/bench stats.
    """
    week = data_type.removeprefix("rosters_week")
    teams = _collection_items(_league_subresource(data, "teams") or {}, "team")
    rows = []
    for team in teams:
        tflat = _flatten(team)
        roster = _flatten(tflat.get("roster", {}))
        players = _collection_items(
            _flatten(roster.get("0", {})).get("players", {})
            or roster.get("players", {}),
            "player",
        )
        for player in players:
            pflat = _flatten(player)
            selected = _flatten(pflat.get("selected_position", {}))
            points = _flatten(pflat.get("player_points", {}))
            name = _flatten(pflat.get("name", {}))
            rows.append(
                {
                    "team_key": tflat.get("team_key"),
                    "week": week,
                    "player_key": pflat.get("player_key"),
                    "player_name": name.get("full"),
                    "position": pflat.get("display_position"),
                    "selected_position": selected.get("position"),
                    "points": points.get("total"),
                }
            )
    return {"rosters": rows}


def _filter_draft_picks(data: dict[str, Any], _season: str, _dt: str) -> dict[str, Any]:
    results = _collection_items(
        _league_subresource(data, "draft_results") or {}, "draft_result"
    )
    picks = [
        {
            "pick": _flatten(r).get("pick"),
            "round": _flatten(r).get("round"),
            "team_key": _flatten(r).get("team_key"),
            "player_key": _flatten(r).get("player_key"),
            "cost": _flatten(r).get("cost"),
        }
        for r in results
    ]
    return {"draft_picks": picks}


def _filter_transactions(
    data: dict[str, Any], _season: str, _dt: str
) -> dict[str, Any]:
    txns = _collection_items(
        _league_subresource(data, "transactions") or {}, "transaction"
    )
    kept = []
    for txn in txns:
        flat = _flatten(txn)
        if flat.get("status") != "successful":
            continue
        if flat.get("type") not in ("add", "drop", "add/drop", "trade"):
            continue
        players = _collection_items(_flatten(flat.get("players", {})), "player")
        items = []
        for player in players:
            pflat = _flatten(player)
            tdata = _flatten(pflat.get("transaction_data", {}))
            items.append(
                {
                    "player_key": pflat.get("player_key"),
                    "type": tdata.get("type"),
                    "source_team_key": tdata.get("source_team_key"),
                    "destination_team_key": tdata.get("destination_team_key"),
                }
            )
        kept.append(
            {
                "transaction_key": flat.get("transaction_key"),
                "type": flat.get("type"),
                "timestamp": flat.get("timestamp"),
                "faab_bid": flat.get("faab_bid"),
                "items": items,
            }
        )
    return {"transactions": kept}


_YAHOO_DATA_FILTERS: dict[str, Callable[[dict, str, str], dict]] = {
    "settings": _filter_settings,
    "standings": _filter_standings,
    "teams": _filter_teams,
    "draft_picks": _filter_draft_picks,
    "transactions": _filter_transactions,
}


class YahooClient:
    """Yahoo Fantasy API client for onboarding a league's full season history.

    Attributes:
        league_id: The entered numeric Yahoo league id (current season).
        owner_user_id: The onboarding owner's Clerk user id (whose linked Yahoo token is used).
        is_refresh: When True, only the current season is fetched.
    """

    def __init__(
        self,
        league_id: str,
        owner_user_id: str,
        is_refresh: bool = False,
        token_provider: Callable[[], str] | None = None,
    ):
        """Constructor.

        Args:
            league_id: Entered numeric Yahoo league id.
            owner_user_id: Clerk user id whose linked Yahoo token authorizes the fetch.
            is_refresh: If True, resolve/fetch only the current season.
            token_provider: Callable returning a valid Yahoo access token (refreshing as needed).
                Defaults to the shared token engine keyed by ``owner_user_id`` — injected in tests.
        """
        self.league_id = str(league_id)
        self.owner_user_id = owner_user_id
        self.is_refresh = is_refresh
        self._token_provider = token_provider or self._default_token_provider
        # season -> {"league_key", "start_week", "end_week", "current_week"}
        self._season_meta: dict[str, dict[str, Any]] = {}
        self.seasons = self._resolve_seasons()

    def _default_token_provider(self) -> str:
        from common.yahoo_tokens import from_env

        return from_env().get_valid_access_token(self.owner_user_id)

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token_provider()}"}

    def get_seasons(self) -> list[str]:
        """Return the list of seasons this league lineage has been active."""
        return self.seasons

    def _get_json(self, url: str) -> dict[str, Any]:
        """Synchronous authenticated GET returning parsed JSON (used by season resolution)."""
        response = requests.get(url, headers=self._auth_headers(), timeout=(5, 30))
        response.raise_for_status()
        return response.json()

    def _resolve_seasons(self) -> list[str]:
        """Resolve the league_key/season history from the owner's Yahoo leagues.

        Enumerates the owner's NFL leagues (verifying membership), finds the entered league id,
        then walks the ``renew`` chain backward to include every prior season. When ``is_refresh``
        only the current season is kept.
        """
        url = (
            f"{YAHOO_BASE_URL}/users;use_login=1/games;game_codes=nfl/leagues"
            "?format=json"
        )
        payload = self._get_json(url)
        leagues_by_id, leagues_by_key = self._parse_user_leagues(payload)

        current = leagues_by_id.get(self.league_id)
        if current is None:
            raise ValueError(
                f"Yahoo league {self.league_id} is not among the linked user's leagues"
            )

        lineage = [current]
        if not self.is_refresh:
            # Walk renew ("{game_id}_{league_id}" -> "{game_key}.l.{league_id}") backward.
            node = current
            while node.get("renew"):
                renew_key = _renew_to_league_key(node["renew"])
                prior = leagues_by_key.get(renew_key)
                if prior is None:
                    break
                lineage.append(prior)
                node = prior

        for league in lineage:
            season = str(league.get("season"))
            self._season_meta[season] = {
                "league_key": league.get("league_key"),
                "start_week": _to_int(league.get("start_week"), 1),
                "end_week": _to_int(league.get("end_week"), 17),
                "current_week": _to_int(league.get("current_week"), None),
            }
        seasons = sorted(self._season_meta)
        logger.info(
            "Resolved Yahoo league seasons: league_id=%s season_count=%d seasons=%s",
            self.league_id,
            len(seasons),
            seasons,
        )
        return seasons

    def _parse_user_leagues(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, dict], dict[str, dict]]:
        """Parse the user→games→leagues enumeration into id- and key-indexed league metas."""
        by_id: dict[str, dict] = {}
        by_key: dict[str, dict] = {}
        users = _collection_items(
            payload.get("fantasy_content", {}).get("users", {}), "user"
        )
        for user in users:
            games = _collection_items(_flatten(user).get("games", {}), "game")
            for game in games:
                leagues = _collection_items(_flatten(game).get("leagues", {}), "league")
                for league in leagues:
                    meta = _flatten(league[0] if isinstance(league, list) else league)
                    if meta.get("league_id"):
                        by_id[str(meta["league_id"])] = meta
                    if meta.get("league_key"):
                        by_key[meta["league_key"]] = meta
        return by_id, by_key

    def _build_request_urls(self) -> list[tuple[str, str, str]]:
        """Build (season, data_type, url) tuples for every per-league sub-resource."""
        urls: list[tuple[str, str, str]] = []
        for season, meta in self._season_meta.items():
            key = meta["league_key"]
            sub_map = {
                "settings": f"{YAHOO_BASE_URL}/league/{key}/settings?format=json",
                "standings": f"{YAHOO_BASE_URL}/league/{key}/standings?format=json",
                "teams": f"{YAHOO_BASE_URL}/league/{key}/teams?format=json",
                "draft_picks": f"{YAHOO_BASE_URL}/league/{key}/draftresults?format=json",
                "transactions": f"{YAHOO_BASE_URL}/league/{key}/transactions;types=add,drop,trade?format=json",
            }
            for data_type in DATA_FETCH_TYPES:
                urls.append((season, data_type, sub_map[data_type]))
            last_week = meta.get("current_week") or meta["end_week"]
            for week in range(meta["start_week"], last_week + 1):
                urls.append(
                    (
                        season,
                        f"matchups_week{week}",
                        f"{YAHOO_BASE_URL}/league/{key}/scoreboard;week={week}?format=json",
                    )
                )
                # One call per week returns every team's roster + weekly player points,
                # which the processor joins to matchups for starter/bench lineup stats.
                urls.append(
                    (
                        season,
                        f"rosters_week{week}",
                        f"{YAHOO_BASE_URL}/league/{key}/teams/roster;week={week}/players/stats;type=week;week={week}?format=json",
                    )
                )
        logger.info(
            "Built Yahoo request URLs: league_id=%s total_requests=%d",
            self.league_id,
            len(urls),
        )
        return urls

    async def fetch_all(self) -> list[dict[str, Any]]:
        """Fetch every per-league sub-resource concurrently and normalize the results."""
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            results = await run_fetches(
                session,
                self._build_request_urls(),
                self._fetch,
                concurrency=YAHOO_CONCURRENCY,
            )
            return self._process_api_results(results)

    async def _fetch(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        url_data: tuple[str, str, str],
    ) -> dict[str, Any]:
        """Fetch one Yahoo URL, refreshing the token once on a 401."""
        season, data_type, url = url_data
        async with semaphore:
            try:
                data = await self._fetch_with_auth_retry(session, url)
                logger.info("Successfully fetched url: %s", url)
                return {"season": season, "data_type": data_type, "data": data}
            except Exception as e:  # noqa: BLE001 — isolate one request's failure
                logger.error(
                    "Failed request for url: %s season=%s data_type=%s %s",
                    url,
                    season,
                    data_type,
                    describe_fetch_error(e),
                )
                return {"season": season, "data_type": data_type, "data": None}

    async def _fetch_with_auth_retry(
        self, session: aiohttp.ClientSession, url: str
    ) -> Any:
        """fetch_with_retry, refreshing the Bearer token once on a 401 (expired mid-run)."""
        try:
            return await fetch_with_retry(session, url, headers=self._auth_headers())
        except aiohttp.ClientResponseError as e:
            if e.status != 401:
                raise
            logger.info("Yahoo 401 — refreshing token and retrying: %s", url)
            return await fetch_with_retry(session, url, headers=self._auth_headers())

    def _process_api_results(
        self, results: Sequence[dict[str, Any] | BaseException]
    ) -> list[dict[str, Any]]:
        """Validate results and apply the per-type Yahoo filters."""
        processed = []
        for result in validate_api_results(results):
            season = result["season"]
            data_type = result["data_type"]
            data = result["data"]
            if data_type.startswith("matchups"):
                filter_fn = _filter_matchups
            elif data_type.startswith("rosters"):
                filter_fn = _filter_rosters
            else:
                filter_fn = _YAHOO_DATA_FILTERS.get(data_type)
                if filter_fn is None:
                    raise ValueError(f"Invalid data_type: {data_type}")
            processed.append(
                {
                    "season": season,
                    "data_type": data_type,
                    "data": filter_fn(data, season, data_type),
                }
            )
        return processed


def _renew_to_league_key(renew: str) -> str:
    """Convert a Yahoo ``renew`` pointer ``"{game_id}_{league_id}"`` to a ``league_key``."""
    game_id, _, league_id = renew.partition("_")
    return f"{game_id}.l.{league_id}"


def _to_int(value: Any, default: Any) -> Any:
    """Best-effort int coercion with a fallback (Yahoo returns week numbers as strings)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
