"""Tests for onboarder/espn_client.py."""

from unittest.mock import MagicMock, patch

import pytest
import requests


@pytest.fixture(autouse=True)
def default_espn_status():
    """Default the latest-season status request to a drafted league.

    ESPNClient construction now fetches the latest season's status (mTeam +
    mDraftDetail) for both onboard and refresh to resolve seasons and check the
    draft. Patch requests.get so client construction never hits the network;
    tests exercising season resolution override this with their own patch.
    """
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "status": {"previousSeasons": []},
        "draftDetail": {"drafted": True},
    }
    with patch("requests.get", return_value=mock_resp):
        yield mock_resp


class TestFilterFunctions:
    def test_filter_users(self, onboarder_espn_client):
        data = {"members": [{"id": "m1"}], "teams": [{"id": 1}], "extra": "ignored"}
        result = onboarder_espn_client._filter_users(data, "2024", "users")
        assert result == {"members": [{"id": "m1"}], "teams": [{"id": 1}]}

    def test_filter_settings(self, onboarder_espn_client):
        data = {"settings": {"name": "My League"}, "other": "data"}
        result = onboarder_espn_client._filter_settings(data, "2024", "settings")
        assert result == {"settings": {"name": "My League"}}

    def test_filter_draft_picks(self, onboarder_espn_client):
        data = {"draftDetail": {"picks": [{"playerId": 1}]}}
        result = onboarder_espn_client._filter_draft_picks(data, "2024", "draft_picks")
        assert result == {"draft_picks": [{"playerId": 1}]}

    def test_filter_draft_picks_not_yet_drafted(self, onboarder_espn_client):
        # A not-yet-drafted season omits "picks" entirely; tolerate it defensively.
        data = {"draftDetail": {"drafted": False, "inProgress": False}}
        result = onboarder_espn_client._filter_draft_picks(data, "2026", "draft_picks")
        assert result == {"draft_picks": []}

    def test_filter_matchups(self, onboarder_espn_client):
        data = {
            "schedule": [
                {"matchupPeriodId": 1, "home": {"totalPoints": 100}},
                {"matchupPeriodId": 2, "home": {"totalPoints": 90}},
            ]
        }
        result = onboarder_espn_client._filter_matchups(data, "2024", "matchups_week1")
        assert len(result["matchups"]) == 1
        assert result["matchups"][0]["matchupPeriodId"] == 1

    def test_filter_player_scoring_totals_v3(self, onboarder_espn_client):
        data = {
            "players": [
                {
                    "player": {
                        "id": 10,
                        "fullName": "Joe Burrow",
                        "defaultPositionId": 1,
                    },
                    "ratings": {"0": {"totalRating": 312.5}},
                }
            ]
        }
        result = onboarder_espn_client._filter_player_scoring_totals(
            data, "2022", "player_scoring_totals"
        )
        assert result["player_scoring_totals"][0]["player_id"] == 10
        assert result["player_scoring_totals"][0]["total_points"] == 312.5

    def test_filter_player_scoring_totals_v2(self, onboarder_espn_client):
        data = {
            "players": [
                {
                    "player": {
                        "id": 20,
                        "fullName": "Old Player",
                        "defaultPositionId": 2,
                        "stats": [{"appliedTotal": 200.0}],
                    },
                }
            ]
        }
        result = onboarder_espn_client._filter_player_scoring_totals(
            data, "2018", "player_scoring_totals"
        )
        assert result["player_scoring_totals"][0]["total_points"] == 200.0

    def test_filter_player_scoring_totals_no_stats(self, onboarder_espn_client):
        data = {
            "players": [
                {
                    "player": {
                        "id": 30,
                        "fullName": "No Stats",
                        "defaultPositionId": 3,
                        "stats": [],
                    },
                }
            ]
        }
        result = onboarder_espn_client._filter_player_scoring_totals(
            data, "2018", "player_scoring_totals"
        )
        assert result["player_scoring_totals"][0]["total_points"] is None


class TestESPNClientInit:
    def test_init_without_cookies(self, onboarder_espn_client):
        with patch.object(
            onboarder_espn_client.ESPNClient,
            "_get_league_seasons",
            return_value=["2023", "2024"],
        ):
            client = onboarder_espn_client.ESPNClient(
                league_id="123", latest_season="2024"
            )
        assert client.league_id == "123"
        assert client.s2 is None
        assert client.swid is None

    def test_init_with_both_cookies(self, onboarder_espn_client):
        with patch.object(
            onboarder_espn_client.ESPNClient,
            "_get_league_seasons",
            return_value=["2024"],
        ):
            client = onboarder_espn_client.ESPNClient(
                league_id="123", latest_season="2024", s2="abc", swid="{xyz}"
            )
        assert client.s2 == "abc"
        assert client.swid == "{xyz}"

    def test_init_raises_when_only_one_cookie_provided(self, onboarder_espn_client):
        with pytest.raises(ValueError, match="Both swid and s2"):
            onboarder_espn_client.ESPNClient(
                league_id="123", latest_season="2024", s2="abc"
            )

    def test_init_is_refresh_uses_single_season(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2024", is_refresh=True
        )
        assert client.seasons == ["2024"]


class TestESPNClientGetSeasons:
    def test_get_league_seasons_success(self, onboarder_espn_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": {"previousSeasons": [2022, 2023]},
            "draftDetail": {"drafted": True},
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            client = onboarder_espn_client.ESPNClient(
                league_id="123", latest_season="2024"
            )
        assert "2022" in client.seasons
        assert "2024" in client.seasons

    def test_get_league_seasons_excludes_undrafted_latest(self, onboarder_espn_client):
        # A multi-season league whose latest season has not drafted: prior seasons
        # onboard, the undrafted latest season is excluded.
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": {"previousSeasons": [2024, 2025]},
            "draftDetail": {"drafted": False, "inProgress": False},
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            client = onboarder_espn_client.ESPNClient(
                league_id="123", latest_season="2026"
            )
        assert client.seasons == ["2024", "2025"]
        assert "2026" not in client.seasons

    def test_get_league_seasons_new_undrafted_league_is_empty(
        self, onboarder_espn_client
    ):
        # A brand-new league whose only season has not drafted yields no seasons,
        # which the handler surfaces as NOT_STARTED.
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": {"previousSeasons": []},
            "draftDetail": {"drafted": False, "inProgress": False},
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            client = onboarder_espn_client.ESPNClient(
                league_id="123", latest_season="2026"
            )
        assert client.seasons == []

    def test_refresh_excludes_undrafted_latest(self, onboarder_espn_client):
        # A refresh of a not-yet-drafted current season yields no seasons (no-op).
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": {"previousSeasons": [2024, 2025]},
            "draftDetail": {"drafted": False, "inProgress": False},
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            client = onboarder_espn_client.ESPNClient(
                league_id="123", latest_season="2026", is_refresh=True
            )
        assert client.seasons == []

    def test_refresh_drafted_latest_uses_single_season(self, onboarder_espn_client):
        # A refresh of a drafted current season considers only that season.
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": {"previousSeasons": [2024, 2025]},
            "draftDetail": {"drafted": True},
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            client = onboarder_espn_client.ESPNClient(
                league_id="123", latest_season="2026", is_refresh=True
            )
        assert client.seasons == ["2026"]

    def test_get_league_seasons_http_error(self, onboarder_espn_client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("403")
        with (
            patch("requests.get", return_value=mock_resp),
            pytest.raises(requests.exceptions.HTTPError),
        ):
            onboarder_espn_client.ESPNClient(league_id="123", latest_season="2024")


class TestESPNClientConstructRequestUrl:
    def setup_method(self):
        self._base = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2024/segments/0/leagues/123"

    def _get_client(self, onboarder_espn_client):
        return onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2024", is_refresh=True
        )

    def test_users_url(self, onboarder_espn_client):
        client = self._get_client(onboarder_espn_client)
        url = client._construct_request_url(self._base, "users")
        assert "view=mTeam" in url

    def test_settings_url(self, onboarder_espn_client):
        client = self._get_client(onboarder_espn_client)
        url = client._construct_request_url(self._base, "settings")
        assert "mSettings" in url

    def test_draft_picks_url(self, onboarder_espn_client):
        client = self._get_client(onboarder_espn_client)
        url = client._construct_request_url(self._base, "draft_picks")
        assert "mDraftDetail" in url

    def test_matchups_url_with_week(self, onboarder_espn_client):
        client = self._get_client(onboarder_espn_client)
        url = client._construct_request_url(self._base, "matchups", week=5)
        assert "scoringPeriodId=5" in url

    def test_player_scoring_totals_url(self, onboarder_espn_client):
        client = self._get_client(onboarder_espn_client)
        url = client._construct_request_url(self._base, "player_scoring_totals")
        assert "kona_player_info" in url

    def test_invalid_data_type_raises(self, onboarder_espn_client):
        client = self._get_client(onboarder_espn_client)
        with pytest.raises(ValueError, match="Invalid data_type"):
            client._construct_request_url(self._base, "invalid_type")


class TestESPNClientMakeCookies:
    def test_no_cookies_returns_empty(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2024", is_refresh=True
        )
        assert client._make_cookies_dict() == {}

    def test_both_cookies_returned(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123",
            latest_season="2024",
            s2="abc",
            swid="{xyz}",
            is_refresh=True,
        )
        cookies = client._make_cookies_dict()
        assert cookies["espn_s2"] == "abc"
        assert cookies["SWID"] == "{xyz}"


class TestESPNClientBuildAllRequestUrls:
    def test_extended_season_has_18_weeks_for_matchups(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2021", is_refresh=True
        )
        matchup_urls = [u for u in client.request_urls if "matchups" in u[1]]
        assert len(matchup_urls) == 18

    def test_pre_extended_season_has_17_weeks_for_matchups(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2020", is_refresh=True
        )
        matchup_urls = [u for u in client.request_urls if "matchups" in u[1]]
        assert len(matchup_urls) == 17

    def test_v2_season_uses_leagueHistory_url(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2018", is_refresh=True
        )
        urls = [u[2] for u in client.request_urls]
        assert any("leagueHistory" in url for url in urls)


class TestESPNClientGetSeasonsList:
    def test_get_seasons_returns_list(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2024", is_refresh=True
        )
        seasons = client.get_seasons()
        assert seasons == ["2024"]


class TestESPNClientProcessApiResults:
    def test_process_valid_results(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2024", is_refresh=True
        )
        results = [
            {
                "season": "2024",
                "data_type": "users",
                "data": {"members": [], "teams": []},
            }
        ]
        processed = client._process_api_results(results)
        assert len(processed) == 1
        assert "members" in processed[0]["data"]

    def test_process_matchups_data(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2024", is_refresh=True
        )
        results = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": {"schedule": [{"matchupPeriodId": 1, "home": {}, "away": {}}]},
            }
        ]
        processed = client._process_api_results(results)
        assert "matchups" in processed[0]["data"]

    def test_raises_on_invalid_data_type(self, onboarder_espn_client):
        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2024", is_refresh=True
        )
        results = [
            {
                "season": "2024",
                "data_type": "bad_type",
                "data": {},
            }
        ]
        with pytest.raises(ValueError):
            client._process_api_results(results)


class TestESPNClientFetch:
    def _client(self, mod):
        return mod.ESPNClient(league_id="123", latest_season="2024", is_refresh=True)

    async def test_fetch_returns_data(self, onboarder_espn_client):
        import asyncio
        from unittest.mock import AsyncMock

        client = self._client(onboarder_espn_client)
        with patch.object(
            onboarder_espn_client,
            "fetch_with_retry",
            AsyncMock(return_value={"members": []}),
        ):
            result = await client._fetch(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "users", "http://x"),
            )
        assert result == {
            "season": "2024",
            "data_type": "users",
            "data": {"members": []},
        }

    async def test_fetch_unwraps_list_response(self, onboarder_espn_client):
        import asyncio
        from unittest.mock import AsyncMock

        client = self._client(onboarder_espn_client)
        with patch.object(
            onboarder_espn_client,
            "fetch_with_retry",
            AsyncMock(return_value=[{"first": 1}, {"second": 2}]),
        ):
            result = await client._fetch(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "users", "http://x"),
            )
        assert result["data"] == {"first": 1}  # first element of the list

    async def test_fetch_player_scoring_totals_sets_filter_header(
        self, onboarder_espn_client
    ):
        import asyncio
        from unittest.mock import AsyncMock

        client = self._client(onboarder_espn_client)
        mock_fetch = AsyncMock(return_value={"players": []})
        with patch.object(onboarder_espn_client, "fetch_with_retry", mock_fetch):
            await client._fetch(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "player_scoring_totals", "http://x"),
            )
        headers = mock_fetch.call_args[1]["headers"]
        assert "X-Fantasy-Filter" in headers

    async def test_fetch_returns_none_on_error(self, onboarder_espn_client):
        import asyncio
        from unittest.mock import AsyncMock

        client = self._client(onboarder_espn_client)
        with patch.object(
            onboarder_espn_client,
            "fetch_with_retry",
            AsyncMock(side_effect=RuntimeError("boom")),
        ):
            result = await client._fetch(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "users", "http://x"),
            )
        assert result == {"season": "2024", "data_type": "users", "data": None}


class TestESPNClientFetchAll:
    async def test_fetch_all_processes_results(self, onboarder_espn_client):
        from unittest.mock import AsyncMock

        client = onboarder_espn_client.ESPNClient(
            league_id="123",
            latest_season="2024",
            s2="abc",
            swid="{xyz}",
            is_refresh=True,
        )
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        session_cm.__aexit__ = AsyncMock(return_value=False)
        raw_results = [
            {
                "season": "2024",
                "data_type": "users",
                "data": {"members": [], "teams": []},
            }
        ]
        with (
            patch("aiohttp.ClientSession", return_value=session_cm),
            patch.object(
                onboarder_espn_client,
                "run_fetches",
                AsyncMock(return_value=raw_results),
            ),
        ):
            processed = await client.fetch_all()
        assert processed[0]["data_type"] == "users"
        assert "members" in processed[0]["data"]

    async def test_fetch_all_without_cookies(self, onboarder_espn_client):
        from unittest.mock import AsyncMock

        client = onboarder_espn_client.ESPNClient(
            league_id="123", latest_season="2024", is_refresh=True
        )
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        session_cm.__aexit__ = AsyncMock(return_value=False)
        with (
            patch("aiohttp.ClientSession", return_value=session_cm) as mock_session,
            patch.object(
                onboarder_espn_client, "run_fetches", AsyncMock(return_value=[])
            ),
        ):
            await client.fetch_all()
        # No cookies -> ClientSession is created with cookies=None.
        assert mock_session.call_args[1]["cookies"] is None
