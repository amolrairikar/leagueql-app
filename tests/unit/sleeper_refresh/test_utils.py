"""Tests for sleeper_refresh/utils.py."""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestSetupLogger:
    def test_adds_handler_when_no_handlers_exist(self):
        import logging
        import utils as sleeper_refresh_utils

        log = logging.getLogger("leagueql")
        original_handlers = log.handlers[:]
        log.handlers = []
        try:
            sleeper_refresh_utils.setup_logger()
            assert len(log.handlers) == 1
        finally:
            log.handlers = original_handlers


class TestJsonFormatter:
    def test_format_returns_json_with_required_keys(self):
        import utils as sleeper_refresh_utils

        formatter = sleeper_refresh_utils.JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=(),
            exc_info=None,
            func="test_func",
        )
        result = json.loads(formatter.format(record))
        assert result["level"] == "INFO"
        assert result["message"] == "hello world"
        assert result["function"] == "test_func"
        assert "timestamp" in result


class TestGetNflState:
    def test_returns_dict_on_success(self):
        import utils as sleeper_refresh_utils

        mock_response = MagicMock()
        mock_response.json.return_value = {"season_type": "regular", "week": 5}

        with patch.object(sleeper_refresh_utils, "requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            result = sleeper_refresh_utils.get_nfl_state()

        assert result == {"season_type": "regular", "week": 5}
        mock_response.raise_for_status.assert_called_once()

    def test_raises_on_http_error(self):
        import utils as sleeper_refresh_utils

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500"
        )

        with patch.object(sleeper_refresh_utils, "requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            with pytest.raises(requests.exceptions.HTTPError):
                sleeper_refresh_utils.get_nfl_state()


class TestGetSleeperLeagues:
    def test_returns_most_recent_league_per_canonical(self):
        import utils as sleeper_refresh_utils

        items = [
            {
                "canonical_league_id": {"S": "canon-1"},
                "league_id": {"S": "league-2024"},
                "seasons": {"SS": ["2023", "2024"]},
            },
            {
                "canonical_league_id": {"S": "canon-1"},
                "league_id": {"S": "league-2023"},
                "seasons": {"SS": ["2023"]},
            },
        ]

        with patch.object(sleeper_refresh_utils, "_dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Items": items}
            result = sleeper_refresh_utils.get_sleeper_leagues()

        assert len(result) == 1
        assert result[0] == "league-2024"

    def test_handles_pagination(self):
        import utils as sleeper_refresh_utils

        items_page1 = [
            {
                "canonical_league_id": {"S": "canon-1"},
                "league_id": {"S": "league-1"},
                "seasons": {"SS": ["2024"]},
            }
        ]
        items_page2 = [
            {
                "canonical_league_id": {"S": "canon-2"},
                "league_id": {"S": "league-2"},
                "seasons": {"SS": ["2024"]},
            }
        ]

        with patch.object(sleeper_refresh_utils, "_dynamodb_client") as mock_ddb:
            mock_ddb.query.side_effect = [
                {"Items": items_page1, "LastEvaluatedKey": {"PK": "some-key"}},
                {"Items": items_page2},
            ]
            result = sleeper_refresh_utils.get_sleeper_leagues()

        assert len(result) == 2

    def test_returns_empty_list_when_no_items(self):
        import utils as sleeper_refresh_utils

        with patch.object(sleeper_refresh_utils, "_dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Items": []}
            result = sleeper_refresh_utils.get_sleeper_leagues()

        assert result == []

    def test_skips_items_with_missing_fields(self):
        import utils as sleeper_refresh_utils

        items = [
            {"canonical_league_id": {"S": "canon-1"}},  # missing league_id and seasons
        ]

        with patch.object(sleeper_refresh_utils, "_dynamodb_client") as mock_ddb:
            mock_ddb.query.return_value = {"Items": items}
            result = sleeper_refresh_utils.get_sleeper_leagues()

        assert result == []


class TestInvokeOnboarderLambda:
    def test_successful_invocation(self):
        import utils as sleeper_refresh_utils

        with patch.object(sleeper_refresh_utils, "_lambda_client") as mock_lambda:
            mock_lambda.invoke.return_value = {"StatusCode": 202}
            sleeper_refresh_utils.invoke_onboarder_lambda("league-123")

        call_kwargs = mock_lambda.invoke.call_args[1]
        payload = json.loads(call_kwargs["Payload"])
        assert payload["requestType"] == "REFRESH"
        assert payload["body"]["leagueId"] == "league-123"
        assert payload["body"]["platform"] == "SLEEPER"

    def test_raises_on_non_202_status(self):
        import utils as sleeper_refresh_utils

        with patch.object(sleeper_refresh_utils, "_lambda_client") as mock_lambda:
            mock_lambda.invoke.return_value = {"StatusCode": 500}
            with pytest.raises(Exception, match="Lambda invocation failed"):
                sleeper_refresh_utils.invoke_onboarder_lambda("league-123")
