"""Tests for sleeper_refresh/handler.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


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

    def test_raises_when_nfl_state_fails(self, sleeper_refresh_handler):
        """A failed NFL-state fetch must raise so the Lambda Errors alarm fires,
        rather than silently reporting a failed run as a 502."""
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                side_effect=Exception("network error"),
            ),
            pytest.raises(Exception, match="network error"),
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())

    def test_raises_when_nfl_state_missing_season(self, sleeper_refresh_handler):
        """NFL state past the season_type/week gate but lacking a parseable
        `season` is indeterminate: the handler must raise (no leagues refreshed)
        so the error alarm fires rather than refreshing without a season reference."""
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5},
            ),
            patch.object(
                sleeper_refresh_handler, "get_sleeper_leagues"
            ) as mock_get_leagues,
            pytest.raises(KeyError),
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())
        mock_get_leagues.assert_not_called()

    def test_raises_when_get_leagues_fails(self, sleeper_refresh_handler):
        """A failed league-list query must raise (refreshes zero leagues) so the
        Lambda Errors alarm fires instead of reporting success."""
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                side_effect=Exception("DDB error"),
            ),
            pytest.raises(Exception, match="DDB error"),
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())

    def test_returns_200_when_no_leagues(self, sleeper_refresh_handler):
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
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
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
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

    def test_logged_correlation_id_matches_invoked_one(self, sleeper_refresh_handler):
        """The correlation_id logged on success must be the same one sent to the
        onboarder (regression: a second uuid4() was previously logged)."""
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                return_value=[{"league_id": "lg1", "canonical_league_id": "c1"}],
            ),
            patch.object(
                sleeper_refresh_handler, "invoke_onboarder_lambda"
            ) as mock_invoke,
            patch.object(sleeper_refresh_handler, "logger") as mock_logger,
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())

        invoked_correlation_id = mock_invoke.call_args.kwargs["correlation_id"]
        logged_correlation_ids = [
            call.args[-1]
            for call in mock_logger.info.call_args_list
            if "correlation_id" in (call.args[0] if call.args else "")
        ]
        assert invoked_correlation_id in logged_correlation_ids

    def test_each_league_gets_a_root_span(self, sleeper_refresh_handler):
        """Every refreshed league starts its own root trace (backend/otel-tracing); the cron has
        no inbound context to continue."""
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                return_value=[
                    {"league_id": "lg1", "canonical_league_id": "c1"},
                    {"league_id": "lg2", "canonical_league_id": "c2"},
                ],
            ),
            patch.object(sleeper_refresh_handler, "invoke_onboarder_lambda"),
            patch.object(sleeper_refresh_handler, "traced_handler") as th,
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())

        assert th.call_count == 2
        for call in th.call_args_list:
            assert call.args[0] == "sleeper_refresh.league"
            assert call.kwargs["root"] is True

    def test_raises_when_any_dispatch_fails(self, sleeper_refresh_handler):
        """A dispatch failure never reaches the onboarder (so no onboarder/DLQ
        alarm covers it); the handler must attempt every league and then raise so
        the Lambda Errors alarm fires and EventBridge retries the run."""
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
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
            ) as mock_invoke,
            pytest.raises(RuntimeError, match="Failed to trigger refresh for 1 of 2"),
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())

        # A failure on lg2 must not stop lg1 from being attempted: both are tried.
        assert mock_invoke.call_count == 2


class TestSleeperRefreshJitter:
    """Dispatch jitter (backend/scheduled-sleeper-auto-refresh: "Spread refresh
    dispatches with jitter")."""

    def _make_context(self):
        ctx = MagicMock()
        ctx.aws_request_id = "req-123"
        ctx.function_name = "sleeper-refresh"
        return ctx

    def _leagues(self, n):
        return [
            {"league_id": f"lg{i}", "canonical_league_id": f"c{i}"} for i in range(n)
        ]

    def test_spreads_dispatches_across_window(
        self, sleeper_refresh_handler, monkeypatch
    ):
        """With a window and >1 league, invocations are staggered: time.sleep is
        called with the gaps between sorted per-league offsets, every league is
        still dispatched, and the total delay stays within the window."""
        monkeypatch.setenv("REFRESH_JITTER_WINDOW_SECONDS", "600")
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                return_value=self._leagues(3),
            ),
            # Deterministic offsets (in the leagues' order); the handler sorts them.
            patch.object(
                sleeper_refresh_handler.random,
                "uniform",
                side_effect=[300.0, 60.0, 120.0],
            ),
            patch.object(sleeper_refresh_handler, "time") as mock_time,
            patch.object(
                sleeper_refresh_handler, "invoke_onboarder_lambda"
            ) as mock_invoke,
        ):
            result = sleeper_refresh_handler.lambda_handler({}, self._make_context())

        assert result["statusCode"] == 200
        # Every league dispatched, in offset (jittered) order: lg1(60) lg2(120) lg0(300).
        dispatched = [c.args[0] for c in mock_invoke.call_args_list]
        assert dispatched == ["lg1", "lg2", "lg0"]
        # Gaps between sorted offsets 60,120,300 -> 60,60,180.
        slept = [c.args[0] for c in mock_time.sleep.call_args_list]
        assert slept == [60.0, 60.0, 180.0]
        # Total added delay never exceeds the window.
        assert sum(slept) <= 600.0

    def test_no_sleep_when_window_zero(self, sleeper_refresh_handler, monkeypatch):
        monkeypatch.setenv("REFRESH_JITTER_WINDOW_SECONDS", "0")
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                return_value=self._leagues(3),
            ),
            patch.object(sleeper_refresh_handler, "time") as mock_time,
            patch.object(
                sleeper_refresh_handler, "invoke_onboarder_lambda"
            ) as mock_invoke,
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())

        mock_time.sleep.assert_not_called()
        assert mock_invoke.call_count == 3

    def test_no_sleep_for_single_league(self, sleeper_refresh_handler, monkeypatch):
        """A lone league dispatches immediately even with a window set — a random
        up-to-window delay for one league would be pure waste."""
        monkeypatch.setenv("REFRESH_JITTER_WINDOW_SECONDS", "600")
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                return_value=self._leagues(1),
            ),
            patch.object(sleeper_refresh_handler, "time") as mock_time,
            patch.object(
                sleeper_refresh_handler, "invoke_onboarder_lambda"
            ) as mock_invoke,
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())

        mock_time.sleep.assert_not_called()
        assert mock_invoke.call_count == 1

    def test_invalid_window_falls_back_to_default(
        self, sleeper_refresh_handler, monkeypatch
    ):
        """A non-numeric window is treated as the default (jitter on), not a crash."""
        monkeypatch.setenv("REFRESH_JITTER_WINDOW_SECONDS", "not-a-number")
        with (
            patch.object(
                sleeper_refresh_handler,
                "get_nfl_state",
                return_value={"season_type": "regular", "week": 5, "season": "2024"},
            ),
            patch.object(
                sleeper_refresh_handler,
                "get_sleeper_leagues",
                return_value=self._leagues(2),
            ),
            patch.object(
                sleeper_refresh_handler.random,
                "uniform",
                side_effect=[10.0, 20.0],
            ),
            patch.object(sleeper_refresh_handler, "time") as mock_time,
            patch.object(sleeper_refresh_handler, "invoke_onboarder_lambda"),
        ):
            sleeper_refresh_handler.lambda_handler({}, self._make_context())

        # Default window is in effect, so jitter applied and sleeps happened.
        assert mock_time.sleep.called
