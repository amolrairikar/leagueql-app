"""Tests for sleeper_refresh/handler.py."""

import json
from unittest.mock import MagicMock, patch


class TestLambdaHandlerSleeperRefresh:
    def _make_context(self):
        ctx = MagicMock()
        ctx.aws_request_id = "req-123"
        ctx.function_name = "sleeper-refresh"
        return ctx

    def test_returns_skipped_when_off_season(
        self, sleeper_refresh_handler, sleeper_refresh_utils
    ):
        with patch.object(
            sleeper_refresh_handler,
            "get_nfl_state",
            return_value={"season_type": "off", "week": 1},
        ):
            result = sleeper_refresh_handler.lambda_handler({}, self._make_context())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["status"] == "skipped"

    def test_returns_skipped_when_week_1(self, sleeper_refresh_handler):
        with patch.object(
            sleeper_refresh_handler,
            "get_nfl_state",
            return_value={"season_type": "regular", "week": 1},
        ):
            result = sleeper_refresh_handler.lambda_handler({}, self._make_context())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["status"] == "skipped"

    def test_returns_502_when_nfl_state_fails(self, sleeper_refresh_handler):
        with patch.object(
            sleeper_refresh_handler,
            "get_nfl_state",
            side_effect=Exception("network error"),
        ):
            result = sleeper_refresh_handler.lambda_handler({}, self._make_context())
        assert result["statusCode"] == 502

    def test_returns_500_when_get_leagues_fails(self, sleeper_refresh_handler):
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                side_effect=Exception("DDB error"),
            ),
        ):
            result = sleeper_refresh_handler.lambda_handler({}, self._make_context())
        assert result["statusCode"] == 500

    def test_returns_200_when_no_leagues(self, sleeper_refresh_handler):
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                sleeper_refresh_handler, "get_sleeper_leagues", return_value=[]
            ),
        ):
            result = sleeper_refresh_handler.lambda_handler({}, self._make_context())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "No Sleeper leagues" in body["message"]

    def test_invokes_onboarder_for_each_league(self, sleeper_refresh_handler):
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                return_value=[
                    {"league_id": "lg1", "canonical_league_id": "c1"},
                    {"league_id": "lg2", "canonical_league_id": "c2"},
                ],
            ),
            patch.object(
                sleeper_refresh_handler, "invoke_onboarder_lambda"
            ) as mock_invoke,
        ):
            result = sleeper_refresh_handler.lambda_handler({}, self._make_context())

        assert result["statusCode"] == 200
        assert mock_invoke.call_count == 2
        body = json.loads(result["body"])
        assert body["success_count"] == 2
        assert body["failure_count"] == 0

    def test_counts_failures_when_invoke_raises(self, sleeper_refresh_handler):
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                return_value=[
                    {"league_id": "lg1", "canonical_league_id": "c1"},
                    {"league_id": "lg2", "canonical_league_id": "c2"},
                ],
            ),
            patch.object(
                sleeper_refresh_handler,
                "invoke_onboarder_lambda",
                side_effect=[None, Exception("fail")],
            ),
        ):
            result = sleeper_refresh_handler.lambda_handler({}, self._make_context())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success_count"] == 1
        assert body["failure_count"] == 1
        assert body["total_leagues"] == 2
