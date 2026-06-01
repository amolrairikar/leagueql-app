"""Tests for onboarder/sleeper_client.py."""

import botocore.exceptions
import pytest
import requests
from unittest.mock import MagicMock, patch


def _mock_http_response(json_data, status_code=200, raise_error=False):
    mock = MagicMock()
    mock.json.return_value = json_data
    if raise_error:
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError("err")
    else:
        mock.raise_for_status = MagicMock()
    return mock


class TestResolveSleeperCanonicalLeagueId:
    def test_found_in_dynamodb(self, onboarder_sleeper_client, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({"previous_league_id": "prev-1"})
        ddb_result = {"Item": {"canonical_league_id": {"S": "canonical-abc"}}}

        with (
            patch("requests.get", return_value=http_resp),
            patch.object(
                onboarder_sleeper_client._dynamodb, "get_item", return_value=ddb_result
            ),
        ):
            result = onboarder_sleeper_client.resolve_sleeper_canonical_league_id(
                "new-1"
            )

        assert result == "canonical-abc"

    def test_chain_exhausted_returns_none(self, onboarder_sleeper_client, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({"previous_league_id": "0"})
        with patch("requests.get", return_value=http_resp):
            result = onboarder_sleeper_client.resolve_sleeper_canonical_league_id(
                "new-1"
            )
        assert result is None

    def test_http_error_raises(self, onboarder_sleeper_client, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({}, raise_error=True)
        with patch("requests.get", return_value=http_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                onboarder_sleeper_client.resolve_sleeper_canonical_league_id("new-1")

    def test_dynamodb_client_error_raises(self, onboarder_sleeper_client, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({"previous_league_id": "prev-1"})
        with (
            patch("requests.get", return_value=http_resp),
            patch.object(
                onboarder_sleeper_client._dynamodb,
                "get_item",
                side_effect=botocore.exceptions.ClientError(
                    {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
                ),
            ),
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                onboarder_sleeper_client.resolve_sleeper_canonical_league_id("new-1")

    def test_item_without_canonical_id_continues_chain(
        self, onboarder_sleeper_client, monkeypatch
    ):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_responses = [
            _mock_http_response({"previous_league_id": "prev-1"}),
            _mock_http_response({"previous_league_id": "0"}),
        ]
        ddb_result_no_canonical = {"Item": {}}
        with (
            patch("requests.get", side_effect=http_responses),
            patch.object(
                onboarder_sleeper_client._dynamodb,
                "get_item",
                return_value=ddb_result_no_canonical,
            ),
        ):
            result = onboarder_sleeper_client.resolve_sleeper_canonical_league_id(
                "new-1"
            )
        assert result is None


class TestSleeperClientGetLeagueSeasons:
    def test_single_season_when_is_refresh(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "league-2024", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient(
                "league-2024", is_refresh=True
            )
        assert list(client.season_mapping.keys()) == ["2024"]

    def test_walks_chain_for_all_seasons(self, onboarder_sleeper_client):
        responses = [
            _mock_http_response(
                {
                    "season": "2024",
                    "league_id": "league-2024",
                    "previous_league_id": "league-2023",
                }
            ),
            _mock_http_response(
                {
                    "season": "2023",
                    "league_id": "league-2023",
                    "previous_league_id": "0",
                }
            ),
        ]
        with patch("requests.get", side_effect=responses):
            client = onboarder_sleeper_client.SleeperClient("league-2024")
        assert "2023" in client.season_mapping
        assert "2024" in client.season_mapping

    def test_http_error_raises(self, onboarder_sleeper_client):
        http_resp = _mock_http_response({}, raise_error=True)
        with patch("requests.get", return_value=http_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                onboarder_sleeper_client.SleeperClient("league-2024")

    def test_missing_league_id_raises_runtime_error(self, onboarder_sleeper_client):
        http_resp = _mock_http_response({"season": "2024"})
        with patch("requests.get", return_value=http_resp):
            with pytest.raises(RuntimeError, match="missing field"):
                onboarder_sleeper_client.SleeperClient("league-2024")

    def test_chain_depth_limit_raises(self, onboarder_sleeper_client):
        # previous_league_id never reaches "0", so the shared chain walk must bail
        # out once MAX_CHAIN_DEPTH is exceeded rather than loop forever.
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "lg-prev"}
        )
        with patch("requests.get", return_value=http_resp):
            with pytest.raises(RuntimeError, match="maximum chain depth"):
                onboarder_sleeper_client.SleeperClient("lg")


class TestSleeperClientGetSeasons:
    def test_get_seasons_returns_keys(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "league-2024", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("league-2024")
        seasons = client.get_seasons()
        assert "2024" in seasons


class TestSleeperClientConstructRequestUrl:
    def _make_client(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            return onboarder_sleeper_client.SleeperClient("lg")

    def test_users_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "users")
        assert "/users" in url

    def test_rosters_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "rosters")
        assert "/rosters" in url

    def test_matchups_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "matchups", week=5)
        assert "/matchups/5" in url

    def test_playoff_bracket_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "playoff_bracket")
        assert "winners_bracket" in url

    def test_losers_bracket_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "losers_bracket")
        assert "losers_bracket" in url

    def test_transactions_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "transactions", week=3)
        assert "/transactions/3" in url

    def test_drafts_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "drafts")
        assert "/drafts" in url

    def test_league_settings_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "league_settings")
        assert url.endswith("/league/lg")

    def test_invalid_data_type_raises(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        with pytest.raises(ValueError):
            client._construct_request_url("lg", "bogus")


class TestSleeperClientBuildAllRequestUrls:
    def test_extended_season_has_18_matchup_weeks(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2021", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")
        matchup_urls = [u for u in client.request_urls if "matchups" in u[1]]
        assert len(matchup_urls) == 18

    def test_pre_extended_season_has_17_matchup_weeks(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2020", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")
        matchup_urls = [u for u in client.request_urls if "matchups" in u[1]]
        assert len(matchup_urls) == 17


class TestSleeperClientBuildDraftPickUrls:
    def test_builds_urls_from_draft_results(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")

        results = [
            {"data_type": "drafts", "season": "2024", "data": [{"draft_id": "d1"}]},
            {"data_type": "users", "season": "2024", "data": []},
        ]
        urls = client._build_draft_pick_urls(results)
        assert len(urls) == 1
        assert "/draft/d1/picks" in urls[0][2]

    def test_skips_drafts_without_draft_id(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")

        results = [
            {"data_type": "drafts", "season": "2024", "data": [{}]},
        ]
        urls = client._build_draft_pick_urls(results)
        assert len(urls) == 0

    def test_empty_results_returns_empty(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")

        assert client._build_draft_pick_urls([]) == []
