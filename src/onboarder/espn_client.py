import asyncio
import json
from collections.abc import Sequence
from typing import Any

import aiohttp
import requests
from utils import (
    V2_CUTOFF,
    fetch_one,
    logger,
    matchup_weeks,
    run_fetches,
    validate_api_results,
)
from yarl import URL

DATA_FETCH_TYPES = [
    "users",
    "settings",
    "draft_picks",
    "matchups",
    "player_scoring_totals",
    "transactions",
]
ESPN_PLAYER_FETCH_LIMIT = 1500
# First season whose per-week matchups are fetched from the seasons endpoint even though it
# is at or before V2_CUTOFF: leagueHistory ignores the mBoxscore view, so matchups fetched
# there carry no rosters and the box score comes out empty. The seasons endpoint returns
# full weekly rosters from 2018 on. Other data types keep using leagueHistory.
ESPN_BOXSCORE_SEASONS_ENDPOINT_FROM = 2018


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
    # A not-yet-drafted season's draftDetail omits "picks" entirely
    # (e.g. {"drafted": false, "inProgress": false}). Such seasons are excluded
    # upstream in ESPNClient._get_league_seasons, so this filter should not see one
    # in normal operation; tolerate the absent key defensively rather than KeyError.
    return {"draft_picks": data.get("draftDetail", {}).get("picks", [])}


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


# ESPN transaction types kept in the transactions view (when EXECUTED).
_STORED_TRANSACTION_TYPES = ("FREEAGENT", "WAIVER", "TRADE_UPHOLD", "TRADE_ACCEPT")
_TRADE_TRANSACTION_TYPES = ("TRADE_UPHOLD", "TRADE_ACCEPT")
# kona_playercard requests carry at most this many player IDs (matching espn-api).
ESPN_PLAYER_CARD_BATCH = 40
# data_type of the extra transactions result holding trades recovered from player cards.
TRADE_CARDS_DATA_TYPE = "transactions_trade_cards"


def _trim_transaction(txn: dict[str, Any]) -> dict[str, Any]:
    """Reduce an ESPN transaction — and its ``items`` — to the fields the processor needs."""
    return {
        "id": txn.get("id"),
        "type": txn.get("type"),
        "relatedTransactionId": txn.get("relatedTransactionId"),
        "scoringPeriodId": txn.get("scoringPeriodId"),
        "proposedDate": txn.get("proposedDate"),
        "acceptedDate": txn.get("acceptedDate"),
        "processDate": txn.get("processDate"),
        "bidAmount": txn.get("bidAmount"),
        "teamId": txn.get("teamId"),
        "items": [
            {
                "type": item.get("type"),
                "playerId": item.get("playerId"),
                "fromTeamId": item.get("fromTeamId"),
                "toTeamId": item.get("toTeamId"),
            }
            for item in (txn.get("items") or [])
            if item.get("type") in ("ADD", "DROP", "TRADE")
        ],
    }


def _filter_transactions(
    data: dict[str, Any], _season: str, _data_type: str
) -> dict[str, Any]:
    """
    Trim ESPN ``mTransactions2`` payload to the completed transactions we store.

    Keeps only ``EXECUTED`` waiver claims, free-agent moves, and completed trades
    (DRAFT, ROSTER lineup swaps, and trade proposals are dropped) and reduces each
    record — and each of its ``items`` — to the fields the processor needs, keeping
    the S3 payload lean the way the other ESPN filters do.

    A completed trade is an ``EXECUTED`` ``TRADE_UPHOLD`` (it cleared the league's
    review period) or an ``EXECUTED`` ``TRADE_ACCEPT`` (a league with no review
    period). Proposals and pending accepts never reach ``EXECUTED``.
    """
    return {
        "transactions": [
            _trim_transaction(txn)
            for txn in data.get("transactions", [])
            if txn.get("status") == "EXECUTED"
            and txn.get("type") in _STORED_TRANSACTION_TYPES
        ]
    }


def _trade_key(txn: dict[str, Any]) -> Any:
    """The id that links one trade's records: ``relatedTransactionId``, else ``id``."""
    return txn.get("relatedTransactionId") or txn.get("id")


def _has_trade_items(txn: dict[str, Any]) -> bool:
    return any(item.get("type") == "TRADE" for item in txn.get("items") or [])


def _find_hidden_trades(
    processed_results: list[dict[str, Any]],
) -> dict[str, dict[Any, int | None]]:
    """
    Find executed trades whose traded players ``mTransactions2`` withheld.

    ESPN returns a trade's ``TRADE`` items only when the requesting team is a party;
    for any other trade the executed uphold/accept comes back without them.

    Returns:
        season → trade key → the trade's scoring period.
    """
    hidden: dict[str, dict[Any, int | None]] = {}
    for result in processed_results:
        if not result["data_type"].startswith("transactions"):
            continue
        for txn in result["data"].get("transactions", []):
            if txn.get("type") in _TRADE_TRANSACTION_TYPES and not _has_trade_items(
                txn
            ):
                hidden.setdefault(result["season"], {})[_trade_key(txn)] = txn.get(
                    "scoringPeriodId"
                )
    return hidden


def _rostered_player_ids(
    processed_results: list[dict[str, Any]], season: str, weeks: set[int]
) -> set[int]:
    """Player IDs on any team's box-score roster in the given weeks of a season."""
    wanted = {f"matchups_week{week}" for week in weeks}
    player_ids: set[int] = set()
    for result in processed_results:
        if result["season"] != season or result["data_type"] not in wanted:
            continue
        for matchup in result["data"].get("matchups", []):
            for side in ("home", "away"):
                team = matchup.get(side) or {}
                for roster_key in (
                    "rosterForCurrentScoringPeriod",
                    "rosterForMatchupPeriod",
                ):
                    for entry in (team.get(roster_key) or {}).get("entries", []):
                        player_id = entry.get("playerId")
                        if isinstance(player_id, int):
                            player_ids.add(player_id)
    return player_ids


def _player_card_transactions(wrap: Any) -> list[dict[str, Any]]:
    """Transactions listed on one ``kona_playercard`` player (top level or nested ``player``)."""
    if not isinstance(wrap, dict):
        return []
    inner = wrap.get("player")
    for candidate in (
        wrap.get("transactions"),
        inner.get("transactions") if isinstance(inner, dict) else None,
    ):
        if isinstance(candidate, list):
            return [txn for txn in candidate if isinstance(txn, dict)]
    return []


def _best_card_trades(players: list[Any], keys: set[Any]) -> dict[Any, dict[str, Any]]:
    """Per hidden trade key, the card's EXECUTED ``TRADE_ACCEPT`` with the most trade items."""
    best: dict[Any, dict[str, Any]] = {}
    for wrap in players:
        for txn in _player_card_transactions(wrap):
            if txn.get("type") != "TRADE_ACCEPT" or txn.get("status") != "EXECUTED":
                continue
            key = _trade_key(txn)
            if key not in keys:
                continue
            legs = sum(1 for i in txn.get("items") or [] if i.get("type") == "TRADE")
            if legs == 0:
                continue
            current = best.get(key)
            current_legs = (
                sum(1 for i in current["items"] if i.get("type") == "TRADE")
                if current
                else 0
            )
            if legs > current_legs:
                best[key] = txn
    return best


def _unwrap_list(data: Any, _data_type: str) -> Any:
    """ESPN wraps some season endpoints in a single-element list; unwrap to the object."""
    return data[0] if isinstance(data, list) else data


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
        _get_league_seasons(latest_season, is_refresh): Resolves the seasons to onboard, excluding a not-yet-drafted latest season.
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
        # The latest season's current scoring period, resolved from the status call in
        # _get_league_seasons; bounds the per-week transaction fetch. Defaulted here so
        # it is always defined even when _get_league_seasons is stubbed in tests.
        self.latest_scoring_period: int | None = None
        self.seasons = self._get_league_seasons(
            latest_season=latest_season, is_refresh=is_refresh
        )
        self.request_urls = self._build_all_request_urls()

    def get_seasons(self) -> list[str]:
        """Returns the list of seasons this league has been active."""
        return self.seasons

    def _get_league_seasons(
        self, latest_season: str, is_refresh: bool = False
    ) -> list[str]:
        """
        Gets the list of seasons to onboard, excluding a not-yet-drafted season.

        A season whose draft has not yet occurred (``draftDetail.drafted`` is
        ``False``) is excluded, mirroring the Sleeper ``pre_draft``/``drafting``
        exclusion (backend/league-onboarding): it carries no usable data, so it
        produces no S3 payload, no processed views, and no dropdown entry. ESPN
        reports only completed seasons under ``status.previousSeasons``, so the
        latest season is the only one that can be undrafted; a single
        ``mTeam``+``mDraftDetail`` request on it settles both the season list and
        the draft check.

        For a refresh only the latest season is considered, so an undrafted latest
        season yields an empty list — the caller treats that as a no-op refresh
        that leaves the league's existing data untouched.

        Args:
            latest_season: Most recent season the league was active.
            is_refresh: If True, only the latest season is considered.

        Returns:
            List of seasons to onboard (may be empty when the latest season has
                not drafted).
        """
        url = (
            f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
            f"/seasons/{latest_season}/segments/0/leagues/{self.league_id}"
            f"?view=mTeam&view=mDraftDetail"
        )
        cookies = self._make_cookies_dict()
        response = requests.get(url=url, cookies=cookies, timeout=(5, 30))
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error("Error fetching active seasons for league: %s", e)
            raise

        body = response.json()
        # The latest season's current scoring period bounds the per-week transaction
        # fetch: mTransactions2 returns the CURRENT period's transactions for any
        # scoringPeriodId at or beyond it, so requesting future weeks would return
        # (and duplicate) the current week's data. May be absent for a not-yet-started
        # season; _build_all_request_urls falls back to the full week range.
        self.latest_scoring_period = body.get("status", {}).get("latestScoringPeriod")
        latest_drafted = body.get("draftDetail", {}).get("drafted", False)
        if is_refresh:
            all_seasons = [latest_season] if latest_drafted else []
        else:
            previous_seasons = [
                str(season)
                for season in body.get("status", {}).get("previousSeasons", [])
            ]
            all_seasons = previous_seasons + ([latest_season] if latest_drafted else [])
        logger.info(
            "Resolved ESPN league seasons: league_id=%s season_count=%d seasons=%s "
            "latest_drafted=%s",
            self.league_id,
            len(all_seasons),
            all_seasons,
            latest_drafted,
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
            "transactions": {"view": ["mTransactions2"]},
        }
        if data_type not in param_map:
            raise ValueError(f"Invalid data_type: {data_type}")
        params = param_map[data_type]
        # Matchups and transactions are both fetched per scoring period: a
        # mTransactions2 request without a scoringPeriodId returns only the
        # current period's transactions, so each week must be requested by number.
        if data_type in ("matchups", "transactions") and week:
            params["scoringPeriodId"] = str(week)
        return str(url.update_query(params))

    def _build_all_request_urls(self) -> list[tuple[str, str, str]]:
        """
        Constructs all ESPN Fantasy Football API request URLs needed to fetch data for app.

        Returns:
            List of tuples containing the season, data type, and request URL.
        """
        urls = []
        # Transactions are only fetched for the current (latest) season: ESPN's
        # mTransactions2 view returns no data for past seasons, so requesting them
        # would be wasted calls. Within the latest season they are expanded per
        # scoring period (a mTransactions2 request without a scoringPeriodId returns
        # only the current period's transactions), but bounded to the current period:
        # for any scoringPeriodId at or beyond the current one ESPN returns the
        # current period's transactions, so requesting future weeks would duplicate
        # that week's data. A not-yet-started season leaves latest_scoring_period
        # unset; fall back to the full week range in that case.
        latest_season = max((int(s) for s in self.seasons), default=None)
        for season in self.seasons:
            season_int = int(season)
            for data_type in DATA_FETCH_TYPES:
                if data_type == "transactions" and season_int != latest_season:
                    continue
                use_league_history = season_int <= V2_CUTOFF and not (
                    data_type == "matchups"
                    and season_int >= ESPN_BOXSCORE_SEASONS_ENDPOINT_FROM
                )
                if use_league_history:
                    api_base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{self.league_id}?seasonId={season}"
                else:
                    api_base_url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{self.league_id}"
                if data_type in ("matchups", "transactions"):
                    if data_type == "transactions" and self.latest_scoring_period:
                        weeks = range(1, int(self.latest_scoring_period) + 1)
                    else:
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
            processed = self._process_api_results(results=results)
            processed.extend(await self._recover_hidden_trades(session, processed))
            return processed

    async def _recover_hidden_trades(
        self,
        session: aiohttp.ClientSession,
        processed_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Fill in trades whose players ``mTransactions2`` withheld, from player cards.

        For each season with a hidden trade (an executed uphold/accept without
        ``TRADE`` items), fetches the ``kona_playercard`` view for every player
        rostered in the trade's week and the next one, and keeps each hidden trade's
        executed ``TRADE_ACCEPT`` from those cards (the one with the most traded
        players). The approach follows the espn-api library's ``fill_trade_items``.
        Card requests are only made when a trade is hidden, and a failed card request
        is logged and skipped: the trade it would have filled is then left out by the
        processor rather than failing the run (backend/espn-transactions).

        Returns:
            One ``transactions_trade_cards`` result per season that recovered a trade.
        """
        recovered_results = []
        for season, hidden in _find_hidden_trades(processed_results).items():
            weeks = {
                week + offset
                for week in hidden.values()
                if isinstance(week, int)
                for offset in (0, 1)
            }
            player_ids = sorted(_rostered_player_ids(processed_results, season, weeks))
            batches = {
                f"player_cards_batch{index}": player_ids[
                    start : start + ESPN_PLAYER_CARD_BATCH
                ]
                for index, start in enumerate(
                    range(0, len(player_ids), ESPN_PLAYER_CARD_BATCH)
                )
            }
            url = (
                f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/"
                f"{season}/segments/0/leagues/{self.league_id}?view=kona_playercard"
            )

            async def _fetch_cards(
                session: aiohttp.ClientSession,
                semaphore: asyncio.Semaphore,
                url_data: tuple[str, str, str],
                _season: str = season,
                _batches: dict[str, list[int]] = batches,
            ) -> dict[str, Any]:
                card_filter = {
                    "players": {
                        "filterIds": {"value": _batches[url_data[1]]},
                        "filterStatsForTopScoringPeriodIds": {
                            "value": self.latest_scoring_period or 1,
                            "additionalValue": [f"00{_season}", f"10{_season}"],
                        },
                    }
                }
                return await fetch_one(
                    session,
                    semaphore,
                    url_data,
                    headers={"X-Fantasy-Filter": json.dumps(card_filter)},
                    transform=_unwrap_list,
                )

            results = await run_fetches(
                session,
                [(season, data_type, url) for data_type in batches],
                _fetch_cards,
            )
            players: list[Any] = []
            for result in results:
                if isinstance(result, BaseException) or result.get("data") is None:
                    logger.warning(
                        "Player card request failed; hidden trades may be skipped: "
                        "league_id=%s season=%s",
                        self.league_id,
                        season,
                    )
                    continue
                players.extend(result["data"].get("players") or [])
            recovered = _best_card_trades(players, set(hidden))
            missing = sorted(str(key) for key in set(hidden) - set(recovered))
            logger.info(
                "Recovered hidden ESPN trades from player cards: league_id=%s season=%s "
                "hidden=%d recovered=%d card_requests=%d unrecovered=%s",
                self.league_id,
                season,
                len(hidden),
                len(recovered),
                len(batches),
                missing,
            )
            if recovered:
                recovered_results.append(
                    {
                        "season": season,
                        "data_type": TRADE_CARDS_DATA_TYPE,
                        "data": {
                            "transactions": [
                                _trim_transaction(txn) for txn in recovered.values()
                            ]
                        },
                    }
                )
        return recovered_results

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
        season, data_type, _ = url_data
        headers: dict[str, str] = {}
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

        return await fetch_one(
            session, semaphore, url_data, headers=headers, transform=_unwrap_list
        )

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
            elif data_type.startswith("transactions"):
                filter_fn = _filter_transactions
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
