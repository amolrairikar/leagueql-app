import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from onboarder.sleeper_client import SLEEPER_BASE_URL, SleeperClient


def _make_get_response(season, league_id, previous_league_id="0"):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "season": season,
        "league_id": league_id,
        "previous_league_id": previous_league_id,
    }
    return mock_resp


def make_client(season="2023", league_id="abc", previous_league_id="0"):
    with patch(
        "onboarder.sleeper_client.requests.get",
        return_value=_make_get_response(season, league_id, previous_league_id),
    ):
        return SleeperClient(league_id=league_id)


class TestGetLeagueSeasons:
    def test_single_season_returns_mapping(self):
        with patch(
            "onboarder.sleeper_client.requests.get",
            return_value=_make_get_response("2023", "abc"),
        ):
            client = SleeperClient("abc")

        assert client.season_mapping == {"2023": "abc"}

    def test_multiple_seasons_walks_chain(self):
        responses = [
            _make_get_response("2023", "abc", previous_league_id="xyz"),
            _make_get_response("2022", "xyz", previous_league_id="0"),
        ]
        with patch("onboarder.sleeper_client.requests.get", side_effect=responses):
            client = SleeperClient("abc")

        assert client.season_mapping == {"2023": "abc", "2022": "xyz"}

    def test_missing_previous_league_id_field_stops_loop(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"season": "2023", "league_id": "abc"}
        with patch("onboarder.sleeper_client.requests.get", return_value=mock_resp):
            client = SleeperClient("abc")

        assert client.season_mapping == {"2023": "abc"}

    def test_http_error_raises(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        with patch("onboarder.sleeper_client.requests.get", return_value=mock_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                SleeperClient("abc")

    def test_missing_season_key_raises_runtime_error(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"league_id": "abc"}
        with patch("onboarder.sleeper_client.requests.get", return_value=mock_resp):
            with pytest.raises(
                RuntimeError, match="Unexpected response from Sleeper API"
            ):
                SleeperClient("abc")

    def test_missing_league_id_key_raises_runtime_error(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"season": "2023"}
        with patch("onboarder.sleeper_client.requests.get", return_value=mock_resp):
            with pytest.raises(
                RuntimeError, match="Unexpected response from Sleeper API"
            ):
                SleeperClient("abc")


class TestConstructRequestUrl:
    def setup_method(self):
        self.client = make_client()

    def test_users_url(self):
        url = self.client._construct_request_url("abc", "users")
        assert url == f"{SLEEPER_BASE_URL}/league/abc/users"

    def test_matchups_url(self):
        url = self.client._construct_request_url("abc", "matchups", week=5)
        assert url == f"{SLEEPER_BASE_URL}/league/abc/matchups/5"

    def test_playoff_bracket_url(self):
        url = self.client._construct_request_url("abc", "playoff_bracket")
        assert url == f"{SLEEPER_BASE_URL}/league/abc/winners_bracket"

    def test_transactions_url(self):
        url = self.client._construct_request_url("abc", "transactions", week=3)
        assert url == f"{SLEEPER_BASE_URL}/league/abc/transactions/3"

    def test_drafts_url(self):
        url = self.client._construct_request_url("abc", "drafts")
        assert url == f"{SLEEPER_BASE_URL}/league/abc/drafts"

    def test_invalid_data_type_raises(self):
        with pytest.raises(ValueError, match="Invalid data_type"):
            self.client._construct_request_url("abc", "unknown_type")


class TestBuildAllRequestUrls:
    def test_empty_season_mapping_returns_empty_list(self):
        client = make_client()
        client.season_mapping = {}
        assert client._build_all_request_urls() == []

    def test_matchups_and_transactions_2021_generate_18_weeks(self):
        client = make_client()
        client.season_mapping = {"2021": "abc"}
        urls = client._build_all_request_urls()

        matchup_urls = [u for u in urls if u[1].startswith("matchups_week")]
        transaction_urls = [u for u in urls if u[1].startswith("transactions_week")]
        assert len(matchup_urls) == 18
        assert len(transaction_urls) == 18
        assert any(u[1] == "matchups_week18" for u in matchup_urls)

    def test_matchups_and_transactions_pre_2021_generate_17_weeks(self):
        client = make_client()
        client.season_mapping = {"2020": "abc"}
        urls = client._build_all_request_urls()

        matchup_urls = [u for u in urls if u[1].startswith("matchups_week")]
        transaction_urls = [u for u in urls if u[1].startswith("transactions_week")]
        assert len(matchup_urls) == 17
        assert len(transaction_urls) == 17
        assert not any(u[1] == "matchups_week18" for u in matchup_urls)

    def test_non_week_data_types_generate_single_url_each(self):
        client = make_client()
        client.season_mapping = {"2023": "abc"}
        urls = client._build_all_request_urls()

        users_urls = [u for u in urls if u[1] == "users"]
        playoff_urls = [u for u in urls if u[1] == "playoff_bracket"]
        drafts_urls = [u for u in urls if u[1] == "drafts"]
        assert len(users_urls) == 1
        assert len(playoff_urls) == 1
        assert len(drafts_urls) == 1

    def test_url_tuple_contains_season_data_type_and_url(self):
        client = make_client()
        client.season_mapping = {"2023": "abc"}
        urls = client._build_all_request_urls()

        users_url = next(u for u in urls if u[1] == "users")
        season, data_type, url = users_url
        assert season == "2023"
        assert data_type == "users"
        assert url.startswith("https://")


class TestFetchAll:
    async def test_returns_processed_results(self):
        client = make_client()
        expected = [{"season": "2023", "data_type": "users", "data": []}]

        mock_session = AsyncMock()
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session

        with (
            patch(
                "onboarder.sleeper_client.aiohttp.ClientSession",
                return_value=mock_session_cm,
            ),
            patch.object(
                client,
                "_fetch",
                new_callable=AsyncMock,
                return_value={"season": "2023", "data_type": "users", "data": []},
            ),
            patch(
                "onboarder.sleeper_client.process_api_results", return_value=expected
            ) as mock_process,
        ):
            results = await client.fetch_all()

        assert results == expected
        mock_process.assert_called_once()


class TestFetch:
    async def test_success_returns_data(self):
        client = make_client()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [{"team_id": 1}]

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.get.return_value = mock_get_cm

        result = await client._fetch(
            session=mock_session,
            semaphore=asyncio.Semaphore(10),
            url_data=("2023", "users", "http://example.com"),
        )

        assert result == {
            "season": "2023",
            "data_type": "users",
            "data": [{"team_id": 1}],
        }
        mock_session.get.assert_called_once_with(url="http://example.com")

    async def test_exception_returns_none_data(self):
        client = make_client()

        mock_get_cm = AsyncMock()
        mock_get_cm.__aenter__.side_effect = Exception("Connection error")

        mock_session = MagicMock()
        mock_session.get.return_value = mock_get_cm

        result = await client._fetch(
            session=mock_session,
            semaphore=asyncio.Semaphore(10),
            url_data=("2023", "users", "http://example.com"),
        )

        assert result == {"season": "2023", "data_type": "users", "data": None}
