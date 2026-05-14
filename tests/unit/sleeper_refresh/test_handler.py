"""Tests for sleeper_refresh/handler.py."""

import json
from unittest.mock import patch


class TestLambdaHandler:
    def test_returns_502_when_nfl_state_fetch_fails(self, mock_context):
        import handler as refresh_handler

        with patch.object(
            refresh_handler, "get_nfl_state", side_effect=Exception("connection error")
        ):
            result = refresh_handler.lambda_handler({}, mock_context)

        assert result["statusCode"] == 502

    def test_skips_when_season_type_is_off(self, mock_context):
        import handler as refresh_handler

        with patch.object(
            refresh_handler,
            "get_nfl_state",
            return_value={"season_type": "off", "week": 1},
        ):
            result = refresh_handler.lambda_handler({}, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "skipped"
        assert "off-season" in body["message"]

    def test_skips_when_week_is_one(self, mock_context):
        import handler as refresh_handler

        with patch.object(
            refresh_handler,
            "get_nfl_state",
            return_value={"season_type": "regular", "week": 1},
        ):
            result = refresh_handler.lambda_handler({}, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "skipped"

    def test_returns_200_when_no_leagues(self, mock_context):
        import handler as refresh_handler

        with (
            patch.object(
                refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(refresh_handler, "get_sleeper_leagues", return_value=[]),
        ):
            result = refresh_handler.lambda_handler({}, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "No Sleeper leagues" in body["message"]

    def test_refreshes_all_leagues_and_counts_successes(self, mock_context):
        import handler as refresh_handler

        with (
            patch.object(
                refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                refresh_handler,
                "get_sleeper_leagues",
                return_value=["league-1", "league-2"],
            ),
            patch.object(refresh_handler, "invoke_onboarder_lambda") as mock_invoke,
        ):
            result = refresh_handler.lambda_handler({}, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "succeeded"
        assert body["success_count"] == 2
        assert body["failure_count"] == 0
        assert mock_invoke.call_count == 2

    def test_counts_failures_when_invoke_raises(self, mock_context):
        import handler as refresh_handler

        with (
            patch.object(
                refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                refresh_handler,
                "get_sleeper_leagues",
                return_value=["league-1", "league-2"],
            ),
            patch.object(
                refresh_handler,
                "invoke_onboarder_lambda",
                side_effect=[None, Exception("fail")],
            ),
        ):
            result = refresh_handler.lambda_handler({}, mock_context)

        body = json.loads(result["body"])
        assert body["success_count"] == 1
        assert body["failure_count"] == 1

    def test_returns_500_when_get_leagues_fails(self, mock_context):
        import handler as refresh_handler

        with (
            patch.object(
                refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                refresh_handler,
                "get_sleeper_leagues",
                side_effect=Exception("DynamoDB error"),
            ),
        ):
            result = refresh_handler.lambda_handler({}, mock_context)

        assert result["statusCode"] == 500
