"""Tests for sleeper_refresh/utils.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestGetNflState:
    def test_returns_nfl_state_on_success(self, sleeper_refresh_utils):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"season_type": "regular", "week": 5}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            result = sleeper_refresh_utils.get_nfl_state()
        assert result == {"season_type": "regular", "week": 5}

    def test_raises_on_http_error(self, sleeper_refresh_utils):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("err")
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                sleeper_refresh_utils.get_nfl_state()


class TestGetSleeperLeagues:
    def test_returns_most_recent_league_id_per_canonical(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "canonical-abc"},
                    "league_id": {"S": "lg-2024"},
                    "seasons": {"SS": ["2023", "2024"]},
                },
                {
                    "canonical_league_id": {"S": "canonical-abc"},
                    "league_id": {"S": "lg-2023"},
                    "seasons": {"SS": ["2023"]},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues()
        assert result == ["lg-2024"]

    def test_handles_pagination(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = [
            {
                "Items": [
                    {
                        "canonical_league_id": {"S": "c1"},
                        "league_id": {"S": "lg1"},
                        "seasons": {"SS": ["2024"]},
                    }
                ],
                "LastEvaluatedKey": {"PK": "x"},
            },
            {
                "Items": [
                    {
                        "canonical_league_id": {"S": "c2"},
                        "league_id": {"S": "lg2"},
                        "seasons": {"SS": ["2024"]},
                    }
                ]
            },
        ]
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues()
        assert len(result) == 2
        assert mock_ddb.query.call_count == 2

    def test_returns_empty_list_when_no_items(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {"Items": []}
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues()
        assert result == []

    def test_skips_items_with_missing_fields(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {"canonical_league_id": {"S": "c1"}},  # missing league_id and seasons
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues()
        assert result == []

    def test_multiple_canonical_ids_returns_one_per(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "c1"},
                    "league_id": {"S": "lg1"},
                    "seasons": {"SS": ["2024"]},
                },
                {
                    "canonical_league_id": {"S": "c2"},
                    "league_id": {"S": "lg2"},
                    "seasons": {"SS": ["2024"]},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues()
        assert len(result) == 2


class TestInvokeOnboarderLambda:
    def test_invokes_lambda_successfully(self, sleeper_refresh_utils):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 202}
        with patch.object(sleeper_refresh_utils, "_lambda_client", mock_lambda):
            sleeper_refresh_utils.invoke_onboarder_lambda("league-123")
        mock_lambda.invoke.assert_called_once()
        payload = json.loads(mock_lambda.invoke.call_args[1]["Payload"])
        assert payload["body"]["leagueId"] == "league-123"
        assert payload["requestType"] == "REFRESH"

    def test_raises_when_status_not_202(self, sleeper_refresh_utils):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 500}
        with patch.object(sleeper_refresh_utils, "_lambda_client", mock_lambda):
            with pytest.raises(Exception, match="status code 500"):
                sleeper_refresh_utils.invoke_onboarder_lambda("league-123")
