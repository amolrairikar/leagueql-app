import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from onboarder.espn_client import V2_CUTOFF, ESPNClient


def _mock_seasons_response(previous_seasons=None):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "status": {"previousSeasons": previous_seasons or []}
    }
    return mock_resp


def make_client(
    league_id="123",
    latest_season="2023",
    s2=None,
    swid=None,
    previous_seasons=None,
):
    with patch(
        "onboarder.espn_client.requests.get",
        return_value=_mock_seasons_response(previous_seasons),
    ):
        return ESPNClient(
            league_id=league_id,
            latest_season=latest_season,
            s2=s2,
            swid=swid,
        )


class TestESPNClientInit:
    def test_public_league_success(self):
        client = make_client(previous_seasons=[2021, 2022])
        assert client.league_id == "123"
        assert client.s2 is None
        assert client.swid is None
        assert client.seasons == ["2021", "2022", "2023"]

    def test_private_league_success(self):
        client = make_client(s2="s2val", swid="{swid}")
        assert client.s2 == "s2val"
        assert client.swid == "{swid}"

    def test_only_s2_raises_value_error(self):
        with pytest.raises(ValueError, match="Both swid and s2 must be defined"):
            ESPNClient(league_id="123", latest_season="2023", s2="s2val")

    def test_only_swid_raises_value_error(self):
        with pytest.raises(ValueError, match="Both swid and s2 must be defined"):
            ESPNClient(league_id="123", latest_season="2023", swid="{swid}")


class TestGetLeagueSeasons:
    def test_returns_previous_and_latest_seasons(self):
        client = make_client()
        mock_resp = _mock_seasons_response(previous_seasons=[2020, 2021, 2022])
        with patch("onboarder.espn_client.requests.get", return_value=mock_resp):
            seasons = client._get_league_seasons("2023")
        assert seasons == ["2020", "2021", "2022", "2023"]

    def test_no_previous_seasons_returns_only_latest(self):
        client = make_client()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": {}}
        with patch("onboarder.espn_client.requests.get", return_value=mock_resp):
            seasons = client._get_league_seasons("2023")
        assert seasons == ["2023"]

    def test_http_error_raises(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        with patch("onboarder.espn_client.requests.get", return_value=mock_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                ESPNClient(league_id="123", latest_season="2023")


class TestConstructRequestUrl:
    def setup_method(self):
        self.client = make_client()
        self.base_url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2023/segments/0/leagues/123"

    def test_league_information(self):
        url = self.client._construct_request_url(self.base_url, "league_information")
        assert "view=mTeam" in url

    def test_settings(self):
        url = self.client._construct_request_url(self.base_url, "settings")
        assert "view=mSettings" in url
        assert "view=mTeam" in url

    def test_draft_picks(self):
        url = self.client._construct_request_url(self.base_url, "draft_picks")
        assert "view=mDraftDetail" in url

    def test_player_scoring_totals(self):
        url = self.client._construct_request_url(self.base_url, "player_scoring_totals")
        assert "view=kona_player_info" in url

    def test_matchups_with_week(self):
        url = self.client._construct_request_url(self.base_url, "matchups", week=5)
        assert "view=mBoxscore" in url
        assert "scoringPeriodId=5" in url

    def test_matchups_without_week(self):
        url = self.client._construct_request_url(self.base_url, "matchups", week=None)
        assert "view=mBoxscore" in url
        assert "scoringPeriodId" not in url

    def test_invalid_data_type_raises(self):
        with pytest.raises(ValueError, match="Invalid data_type"):
            self.client._construct_request_url(self.base_url, "unknown_type")


class TestBuildAllRequestUrls:
    def test_v2_season_uses_league_history_url(self):
        client = make_client()
        client.seasons = [str(V2_CUTOFF)]
        urls = client._build_all_request_urls()
        league_info = next(u for u in urls if u[1] == "league_information")
        assert "leagueHistory" in league_info[2]

    def test_v3_season_uses_segments_url(self):
        client = make_client()
        client.seasons = [str(V2_CUTOFF + 1)]
        urls = client._build_all_request_urls()
        league_info = next(u for u in urls if u[1] == "league_information")
        assert "leagueHistory" not in league_info[2]
        assert "segments/0" in league_info[2]

    def test_matchups_2021_or_later_generates_18_weeks(self):
        client = make_client()
        client.seasons = ["2021"]
        urls = client._build_all_request_urls()
        matchup_urls = [u for u in urls if u[1].startswith("matchups_week")]
        assert len(matchup_urls) == 18
        assert any(u[1] == "matchups_week18" for u in matchup_urls)

    def test_matchups_pre_2021_generates_17_weeks(self):
        client = make_client()
        client.seasons = ["2020"]
        urls = client._build_all_request_urls()
        matchup_urls = [u for u in urls if u[1].startswith("matchups_week")]
        assert len(matchup_urls) == 17
        assert not any(u[1] == "matchups_week18" for u in matchup_urls)

    def test_non_matchup_data_type_generates_single_url(self):
        client = make_client()
        client.seasons = ["2023"]
        urls = client._build_all_request_urls()
        league_info_urls = [u for u in urls if u[1] == "league_information"]
        assert len(league_info_urls) == 1

    def test_url_tuple_contains_season_data_type_and_url(self):
        client = make_client()
        client.seasons = ["2023"]
        urls = client._build_all_request_urls()
        season, data_type, url = urls[0]
        assert season == "2023"
        assert isinstance(data_type, str)
        assert url.startswith("https://")


class TestMakeCookiesDict:
    def test_both_s2_and_swid_provided(self):
        client = make_client(s2="abc", swid="{guid}")
        result = client._make_cookies_dict()
        assert result == {"espn_s2": "abc", "SWID": "{guid}"}

    def test_neither_s2_nor_swid_returns_empty(self):
        client = make_client()
        result = client._make_cookies_dict()
        assert result == {}

    def test_only_s2_set(self):
        client = make_client(s2="abc", swid="{guid}")
        client.swid = None
        result = client._make_cookies_dict()
        assert result == {"espn_s2": "abc"}

    def test_only_swid_set(self):
        client = make_client(s2="abc", swid="{guid}")
        client.s2 = None
        result = client._make_cookies_dict()
        assert result == {"SWID": "{guid}"}


class TestBuildCookies:
    def test_returns_cookies_for_private_league(self):
        client = make_client(s2="abc", swid="{guid}")
        result = client._build_cookies()
        assert result == {"espn_s2": "abc", "SWID": "{guid}"}

    def test_returns_none_for_public_league(self):
        client = make_client()
        result = client._build_cookies()
        assert result is None


class TestFetchAll:
    async def test_returns_processed_results(self):
        client = make_client()
        expected = [{"season": "2023", "data_type": "league_information", "data": {}}]

        mock_fetch_result = {
            "season": "2023",
            "data_type": "league_information",
            "data": {},
        }
        mock_session = AsyncMock()
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session

        with (
            patch(
                "onboarder.espn_client.aiohttp.ClientSession",
                return_value=mock_session_cm,
            ),
            patch.object(
                client, "_fetch", new_callable=AsyncMock, return_value=mock_fetch_result
            ),
            patch(
                "onboarder.espn_client.process_api_results", return_value=expected
            ) as mock_process,
        ):
            results = await client.fetch_all()

        assert results == expected
        mock_process.assert_called_once()


class TestFetch:
    def _make_session_mock(self, json_return_value, raise_for_status_effect=None):
        mock_response = AsyncMock()
        if raise_for_status_effect:
            mock_response.raise_for_status = MagicMock(
                side_effect=raise_for_status_effect
            )
        else:
            mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = json_return_value

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.get.return_value = mock_get_cm
        return mock_session

    async def test_non_player_scoring_returns_data(self):
        client = make_client()
        mock_session = self._make_session_mock({"key": "value"})

        result = await client._fetch(
            session=mock_session,
            semaphore=asyncio.Semaphore(10),
            url_data=("2023", "league_information", "http://example.com"),
        )

        assert result == {
            "season": "2023",
            "data_type": "league_information",
            "data": {"key": "value"},
        }
        mock_session.get.assert_called_once_with(url="http://example.com", headers={})

    async def test_player_scoring_totals_adds_filter_header(self):
        client = make_client()
        mock_session = self._make_session_mock({"players": []})

        result = await client._fetch(
            session=mock_session,
            semaphore=asyncio.Semaphore(10),
            url_data=("2023", "player_scoring_totals", "http://example.com"),
        )

        assert result["data"] == {"players": []}
        call_kwargs = mock_session.get.call_args[1]
        headers = call_kwargs["headers"]
        assert "X-Fantasy-Filter" in headers
        filter_val = json.loads(headers["X-Fantasy-Filter"])
        assert filter_val["players"]["limit"] == 1500
        assert filter_val["players"]["sortAppliedStatTotal"]["value"] == "002023"

    async def test_list_response_uses_first_element(self):
        client = make_client()
        mock_session = self._make_session_mock([{"first": "item"}, {"second": "item"}])

        result = await client._fetch(
            session=mock_session,
            semaphore=asyncio.Semaphore(10),
            url_data=("2023", "league_information", "http://example.com"),
        )

        assert result["data"] == {"first": "item"}

    async def test_exception_returns_none_data(self):
        client = make_client()
        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__.side_effect = Exception("Connection error")

        mock_session = MagicMock()
        mock_session.get.return_value = mock_get_cm

        result = await client._fetch(
            session=mock_session,
            semaphore=asyncio.Semaphore(10),
            url_data=("2023", "league_information", "http://example.com"),
        )

        assert result == {
            "season": "2023",
            "data_type": "league_information",
            "data": None,
        }

    async def test_raise_for_status_exception_returns_none_data(self):
        client = make_client()
        mock_session = self._make_session_mock(
            {"key": "value"}, raise_for_status_effect=Exception("403 Forbidden")
        )

        result = await client._fetch(
            session=mock_session,
            semaphore=asyncio.Semaphore(10),
            url_data=("2023", "league_information", "http://example.com"),
        )

        assert result["data"] is None
