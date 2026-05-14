"""Tests for onboarder/espn_client.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestESPNClientInit:
    def test_s2_without_swid_raises_value_error(self):
        from espn_client import ESPNClient

        with pytest.raises(ValueError, match="Both swid and s2 must be defined"):
            ESPNClient(league_id="123", latest_season="2024", s2="some_s2")

    def test_swid_without_s2_raises_value_error(self):
        from espn_client import ESPNClient

        with pytest.raises(ValueError, match="Both swid and s2 must be defined"):
            ESPNClient(league_id="123", latest_season="2024", swid="{SWID}")

    def test_refresh_mode_skips_season_fetch(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        assert client.seasons == ["2024"]

    def test_no_cookies_public_league_ok(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        assert client.s2 is None
        assert client.swid is None


class TestConstructRequestUrl:
    def _make_client(self):
        from espn_client import ESPNClient

        return ESPNClient(league_id="123", latest_season="2024", is_refresh=True)

    @pytest.mark.parametrize(
        "data_type,expected_view",
        [
            ("users", "mTeam"),
            ("settings", "mSettings"),
            ("draft_picks", "mDraftDetail"),
            ("player_scoring_totals", "kona_player_info"),
        ],
    )
    def test_correct_view_param(self, data_type, expected_view):
        client = self._make_client()
        url = client._construct_request_url("https://example.com", data_type)
        assert expected_view in url

    def test_matchups_includes_scoring_period(self):
        client = self._make_client()
        url = client._construct_request_url("https://example.com", "matchups", week=5)
        assert "scoringPeriodId=5" in url

    def test_invalid_data_type_raises(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="Invalid data_type"):
            client._construct_request_url("https://example.com", "invalid_type")


class TestMakeCookiesDict:
    def test_both_cookies(self):
        from espn_client import ESPNClient

        client = ESPNClient(
            league_id="123",
            latest_season="2024",
            s2="s2_value",
            swid="{SWID}",
            is_refresh=True,
        )
        cookies = client._make_cookies_dict()
        assert cookies == {"espn_s2": "s2_value", "SWID": "{SWID}"}

    def test_no_cookies(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        cookies = client._make_cookies_dict()
        assert cookies == {}


class TestBuildAllRequestUrls:
    def test_builds_urls_for_all_data_types(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        urls = client.request_urls
        data_types = {url_data[1] for url_data in urls}
        assert "users" in data_types
        assert "settings" in data_types
        assert "draft_picks" in data_types
        assert any(dt.startswith("matchups_week") for dt in data_types)

    def test_extended_season_has_18_matchup_weeks(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        matchup_urls = [
            u for u in client.request_urls if u[1].startswith("matchups_week")
        ]
        assert len(matchup_urls) == 18

    def test_pre_2021_season_has_17_matchup_weeks(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2020", is_refresh=True)
        matchup_urls = [
            u for u in client.request_urls if u[1].startswith("matchups_week")
        ]
        assert len(matchup_urls) == 17


class TestFilterFunctions:
    def _make_client(self):
        from espn_client import ESPNClient

        return ESPNClient(league_id="123", latest_season="2024", is_refresh=True)

    def test_filter_settings(self):
        client = self._make_client()
        results = [
            {
                "season": "2024",
                "data_type": "settings",
                "data": {"settings": {"name": "My League", "size": 10}},
            }
        ]
        processed = client._process_api_results(results)
        assert processed[0]["data"] == {"settings": {"name": "My League", "size": 10}}

    def test_filter_draft_picks(self):
        client = self._make_client()
        picks = [{"id": 1, "playerId": 123}]
        results = [
            {
                "season": "2024",
                "data_type": "draft_picks",
                "data": {"draftDetail": {"picks": picks}},
            }
        ]
        processed = client._process_api_results(results)
        assert processed[0]["data"] == {"draft_picks": picks}

    def test_filter_player_scoring_totals_modern(self):
        client = self._make_client()
        results = [
            {
                "season": "2024",
                "data_type": "player_scoring_totals",
                "data": {
                    "players": [
                        {
                            "player": {
                                "id": 1,
                                "fullName": "QB One",
                                "defaultPositionId": 1,
                            },
                            "ratings": {"0": {"totalRating": 300.5}},
                        }
                    ]
                },
            }
        ]
        processed = client._process_api_results(results)
        totals = processed[0]["data"]["player_scoring_totals"]
        assert len(totals) == 1
        assert totals[0]["player_id"] == 1
        assert totals[0]["total_points"] == 300.5

    def test_filter_player_scoring_totals_v2(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2018", is_refresh=True)
        results = [
            {
                "season": "2018",
                "data_type": "player_scoring_totals",
                "data": {
                    "players": [
                        {
                            "player": {
                                "id": 2,
                                "fullName": "RB Two",
                                "defaultPositionId": 2,
                                "stats": [{"appliedTotal": 250.0}],
                            }
                        }
                    ]
                },
            }
        ]
        processed = client._process_api_results(results)
        totals = processed[0]["data"]["player_scoring_totals"]
        assert totals[0]["total_points"] == 250.0

    def test_filter_player_scoring_totals_v2_empty_stats(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2018", is_refresh=True)
        results = [
            {
                "season": "2018",
                "data_type": "player_scoring_totals",
                "data": {
                    "players": [
                        {
                            "player": {
                                "id": 3,
                                "fullName": "WR Three",
                                "defaultPositionId": 3,
                                "stats": [],
                            }
                        }
                    ]
                },
            }
        ]
        processed = client._process_api_results(results)
        assert processed[0]["data"]["player_scoring_totals"][0]["total_points"] is None


class TestGetLeagueSeasons:
    def test_fetches_previous_seasons_from_api(self):
        from espn_client import ESPNClient

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"status": {"previousSeasons": [2022, 2023]}}

        with patch("espn_client.requests.get", return_value=mock_response):
            client = ESPNClient(league_id="123", latest_season="2024")

        assert "2022" in client.seasons
        assert "2023" in client.seasons
        assert "2024" in client.seasons

    def test_raises_on_http_error(self):
        from espn_client import ESPNClient
        import requests as req

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError("403")

        with patch("espn_client.requests.get", return_value=mock_response):
            with pytest.raises(req.exceptions.HTTPError):
                ESPNClient(league_id="123", latest_season="2024")

    def test_get_seasons_returns_list(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        seasons = client.get_seasons()
        assert seasons == ["2024"]


class TestBuildAllRequestUrlsV2:
    def test_v2_season_uses_league_history_url(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2018", is_refresh=True)
        urls = client.request_urls
        base_urls = [u[2] for u in urls]
        assert any("leagueHistory" in url for url in base_urls)


class TestFetchAll:
    @pytest.mark.asyncio
    async def test_fetch_all_with_no_urls(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        client.request_urls = []

        with patch("espn_client.aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            with patch("espn_client.validate_api_results", return_value=[]):
                results = await client.fetch_all()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_sets_player_filter_header(self):
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        client.request_urls = [("2024", "player_scoring_totals", "https://example.com")]

        result = {
            "season": "2024",
            "data_type": "player_scoring_totals",
            "data": {"players": []},
        }

        with (
            patch.object(client, "_fetch", return_value=result) as mock_fetch,
            patch("espn_client.aiohttp.ClientSession") as mock_cls,
            patch("espn_client.validate_api_results", return_value=[result]),
        ):
            mock_sess = AsyncMock()
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_sess

            await client.fetch_all()

        mock_fetch.assert_called_once()


class TestFetch:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        import asyncio
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        mock_session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        with patch(
            "espn_client.fetch_with_retry",
            new_callable=AsyncMock,
            return_value={"key": "val"},
        ):
            result = await client._fetch(
                session=mock_session,
                semaphore=semaphore,
                url_data=("2024", "users", "https://example.com"),
            )

        assert result["season"] == "2024"
        assert result["data_type"] == "users"
        assert result["data"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_returns_none_data_on_exception(self):
        import asyncio
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        mock_session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        with patch(
            "espn_client.fetch_with_retry",
            new_callable=AsyncMock,
            side_effect=Exception("network error"),
        ):
            result = await client._fetch(
                session=mock_session,
                semaphore=semaphore,
                url_data=("2024", "users", "https://example.com"),
            )

        assert result["data"] is None
        assert result["season"] == "2024"

    @pytest.mark.asyncio
    async def test_player_scoring_totals_sets_filter_header(self):
        import asyncio
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        mock_session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        with patch(
            "espn_client.fetch_with_retry",
            new_callable=AsyncMock,
            return_value={"players": []},
        ) as mock_fetch:
            await client._fetch(
                session=mock_session,
                semaphore=semaphore,
                url_data=("2024", "player_scoring_totals", "https://example.com"),
            )

        _, call_kwargs = mock_fetch.call_args
        assert "X-Fantasy-Filter" in call_kwargs.get("headers", {})

    @pytest.mark.asyncio
    async def test_list_response_is_unpacked(self):
        import asyncio
        from espn_client import ESPNClient

        client = ESPNClient(league_id="123", latest_season="2024", is_refresh=True)
        mock_session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        with patch(
            "espn_client.fetch_with_retry",
            new_callable=AsyncMock,
            return_value=[{"players": []}],
        ):
            result = await client._fetch(
                session=mock_session,
                semaphore=semaphore,
                url_data=("2024", "users", "https://example.com"),
            )

        assert result["data"] == {"players": []}


class TestProcessApiResults:
    def _make_client(self):
        from espn_client import ESPNClient

        return ESPNClient(league_id="123", latest_season="2024", is_refresh=True)

    def test_filters_users_data(self):
        client = self._make_client()
        results = [
            {
                "season": "2024",
                "data_type": "users",
                "data": {
                    "members": [{"id": "abc"}],
                    "teams": [{"id": 1}],
                    "extra_field": "ignored",
                },
            }
        ]
        processed = client._process_api_results(results)
        assert len(processed) == 1
        assert "members" in processed[0]["data"]
        assert "extra_field" not in processed[0]["data"]

    def test_filters_matchup_data(self):
        client = self._make_client()
        results = [
            {
                "season": "2024",
                "data_type": "matchups_week5",
                "data": {
                    "schedule": [
                        {"matchupPeriodId": "5", "home": {}, "away": {}},
                        {"matchupPeriodId": "6", "home": {}, "away": {}},
                    ]
                },
            }
        ]
        processed = client._process_api_results(results)
        matchups = processed[0]["data"]["matchups"]
        assert len(matchups) == 1
        assert matchups[0]["matchupPeriodId"] == "5"

    def test_raises_on_exception_in_results(self):
        client = self._make_client()
        with pytest.raises(RuntimeError):
            client._process_api_results([RuntimeError("fail")])

    def test_raises_on_none_data(self):
        client = self._make_client()
        results = [{"season": "2024", "data_type": "users", "data": None}]
        with pytest.raises(RuntimeError):
            client._process_api_results(results)

    def test_raises_on_unknown_data_type(self):
        client = self._make_client()
        results = [
            {
                "season": "2024",
                "data_type": "unknown_type",
                "data": {"key": "val"},
            }
        ]
        with pytest.raises(ValueError, match="Invalid data_type"):
            client._process_api_results(results)
