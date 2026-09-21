"""Tests for league_refresh/handler.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


def _sleeper(league_id, canonical):
    return {
        "platform": "SLEEPER",
        "league_id": league_id,
        "canonical_league_id": canonical,
        "owner_user_id": None,
    }


def _yahoo(league_id, canonical, owner):
    return {
        "platform": "YAHOO",
        "league_id": league_id,
        "canonical_league_id": canonical,
        "owner_user_id": owner,
    }


class TestLambdaHandlerLeagueRefresh:
    def _make_context(self):
        ctx = MagicMock()
        ctx.aws_request_id = "req-123"
        ctx.function_name = "league-refresh"
        return ctx

    def test_returns_skipped_when_off_season(self, league_refresh_handler):
        with patch.object(
            league_refresh_handler,
            "get_nfl_state",
            return_value={"season_type": "off", "week": 1},
        ):
            result = league_refresh_handler.lambda_handler({}, self._make_context())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["status"] == "skipped"

    def test_returns_skipped_when_week_1(self, league_refresh_handler):
        with patch.object(
            league_refresh_handler,
            "get_nfl_state",
            return_value={"season_type": "regular", "week": 1},
        ):
            result = league_refresh_handler.lambda_handler({}, self._make_context())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["status"] == "skipped"

    def test_raises_when_nfl_state_fails(self, league_refresh_handler):
        """A failed NFL-state fetch must raise so the Lambda Errors alarm fires,
        rather than silently reporting a failed run as a 502."""
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                side_effect=Exception("network error"),
            ),
            pytest.raises(Exception, match="network error"),
        ):
            league_refresh_handler.lambda_handler({}, self._make_context())

    def test_raises_when_nfl_state_missing_season(self, league_refresh_handler):
        """NFL state past the season_type/week gate but lacking a parseable
        `season` is indeterminate: the handler must raise (no leagues refreshed)
        so the error alarm fires rather than refreshing without a season reference."""
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                league_refresh_handler, "get_leagues_to_refresh"
            ) as mock_get_leagues,
            pytest.raises(KeyError),
        ):
            league_refresh_handler.lambda_handler({}, self._make_context())
        mock_get_leagues.assert_not_called()

    def test_raises_when_get_leagues_fails(self, league_refresh_handler):
        """A failed league-list query must raise (refreshes zero leagues) so the
        Lambda Errors alarm fires instead of reporting success."""
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                league_refresh_handler,
                "get_leagues_to_refresh",
                side_effect=Exception("DDB error"),
            ),
            pytest.raises(Exception, match="DDB error"),
        ):
            league_refresh_handler.lambda_handler({}, self._make_context())

    def test_returns_200_when_no_leagues(self, league_refresh_handler):
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                league_refresh_handler, "get_leagues_to_refresh", return_value=[]
            ),
        ):
            result = league_refresh_handler.lambda_handler({}, self._make_context())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "No leagues" in body["message"]

    def test_invokes_onboarder_for_each_league(self, league_refresh_handler):
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                league_refresh_handler,
                "get_leagues_to_refresh",
                return_value=[
                    _sleeper("lg1", "c1"),
                    _yahoo("y1", "yc1", "user-1"),
                ],
            ),
            patch.object(league_refresh_handler, "pace_dispatch"),
            patch.object(
                league_refresh_handler, "invoke_onboarder_lambda"
            ) as mock_invoke,
        ):
            result = league_refresh_handler.lambda_handler({}, self._make_context())

        assert result["statusCode"] == 200
        assert mock_invoke.call_count == 2
        body = json.loads(result["body"])
        assert body["success_count"] == 2
        assert body["failure_count"] == 0
        # The Yahoo dispatch carries its platform + owner through to the onboarder.
        platforms = {c.kwargs["platform"] for c in mock_invoke.call_args_list}
        assert platforms == {"SLEEPER", "YAHOO"}
        yahoo_call = next(
            c for c in mock_invoke.call_args_list if c.kwargs["platform"] == "YAHOO"
        )
        assert yahoo_call.kwargs["owner_user_id"] == "user-1"

    def test_paces_between_same_platform_dispatches_only(self, league_refresh_handler):
        """A wait separates consecutive same-platform dispatches, but not the first
        dispatch of a platform nor the boundary between platform groups."""
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                league_refresh_handler,
                "get_leagues_to_refresh",
                return_value=[
                    _sleeper("s1", "c1"),
                    _sleeper("s2", "c2"),
                    _yahoo("y1", "yc1", "user-1"),
                    _yahoo("y2", "yc2", "user-2"),
                ],
            ),
            patch.object(league_refresh_handler, "pace_dispatch") as mock_pace,
            patch.object(league_refresh_handler, "invoke_onboarder_lambda"),
        ):
            league_refresh_handler.lambda_handler({}, self._make_context())

        # 2 leagues per platform → exactly one wait within each group (none across groups).
        assert mock_pace.call_count == 2

    def test_logged_correlation_id_matches_invoked_one(self, league_refresh_handler):
        """The correlation_id logged on success must be the same one sent to the
        onboarder (regression: a second uuid4() was previously logged)."""
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                league_refresh_handler,
                "get_leagues_to_refresh",
                return_value=[_sleeper("lg1", "c1")],
            ),
            patch.object(league_refresh_handler, "pace_dispatch"),
            patch.object(
                league_refresh_handler, "invoke_onboarder_lambda"
            ) as mock_invoke,
            patch.object(league_refresh_handler, "logger") as mock_logger,
        ):
            league_refresh_handler.lambda_handler({}, self._make_context())

        invoked_correlation_id = mock_invoke.call_args.kwargs["correlation_id"]
        logged_correlation_ids = [
            call_.args[-1]
            for call_ in mock_logger.info.call_args_list
            if "correlation_id" in (call_.args[0] if call_.args else "")
        ]
        assert invoked_correlation_id in logged_correlation_ids

    def test_each_league_gets_a_root_span(self, league_refresh_handler):
        """Every refreshed league starts its own root trace (backend/otel-tracing); the cron has
        no inbound context to continue."""
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                league_refresh_handler,
                "get_leagues_to_refresh",
                return_value=[_sleeper("lg1", "c1"), _sleeper("lg2", "c2")],
            ),
            patch.object(league_refresh_handler, "pace_dispatch"),
            patch.object(league_refresh_handler, "invoke_onboarder_lambda"),
            patch.object(league_refresh_handler, "traced_handler") as th,
        ):
            league_refresh_handler.lambda_handler({}, self._make_context())

        assert th.call_count == 2
        for th_call in th.call_args_list:
            assert th_call.args[0] == "league_refresh.league"
            assert th_call.kwargs["root"] is True

    def test_raises_when_any_dispatch_fails(self, league_refresh_handler):
        """A dispatch failure never reaches the onboarder (so no onboarder/DLQ
        alarm covers it); the handler must attempt every league and then raise so
        the Lambda Errors alarm fires and EventBridge retries the run."""
        with (
            patch.object(
                league_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                league_refresh_handler,
                "get_leagues_to_refresh",
                return_value=[_sleeper("lg1", "c1"), _sleeper("lg2", "c2")],
            ),
            patch.object(league_refresh_handler, "pace_dispatch"),
            patch.object(
                league_refresh_handler,
                "invoke_onboarder_lambda",
                side_effect=[None, Exception("fail")],
            ) as mock_invoke,
            pytest.raises(RuntimeError, match="Failed to trigger refresh for 1 of 2"),
        ):
            league_refresh_handler.lambda_handler({}, self._make_context())

        # A failure on lg2 must not stop lg1 from being attempted: both are tried.
        assert mock_invoke.call_count == 2
