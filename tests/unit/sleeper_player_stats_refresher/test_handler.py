"""Tests for sleeper_player_stats_refresher/handler.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestFetchNflState:
    def test_returns_state_on_success(self, stats_refresher_handler):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"season_type": "regular", "season": "2024"}
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_refresher_handler, "http_session", mock_session):
            result = stats_refresher_handler.fetch_nfl_state()
        assert result == {"season_type": "regular", "season": "2024"}

    def test_returns_none_on_exception(self, stats_refresher_handler):
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("timeout")

        with patch.object(stats_refresher_handler, "http_session", mock_session):
            result = stats_refresher_handler.fetch_nfl_state()
        assert result is None


class TestFetchStats:
    def test_returns_stats_on_success(self, stats_refresher_handler):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stats": {"pass_yd": 300}}
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_refresher_handler, "http_session", mock_session):
            result = stats_refresher_handler.fetch_stats("p1", "2024")

        assert result == {"pass_yd": 300}

    def test_returns_none_on_404(self, stats_refresher_handler):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_refresher_handler, "http_session", mock_session):
            result = stats_refresher_handler.fetch_stats("p1", "2024")

        assert result is None

    def test_raises_on_http_error(self, stats_refresher_handler):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("err")
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_refresher_handler, "http_session", mock_session):
            with pytest.raises(requests.exceptions.HTTPError):
                stats_refresher_handler.fetch_stats("p1", "2024")

    def test_returns_none_when_data_not_dict(self, stats_refresher_handler):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [1, 2, 3]
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_refresher_handler, "http_session", mock_session):
            result = stats_refresher_handler.fetch_stats("p1", "2024")

        assert result is None


class TestLambdaHandlerRefresher:
    def _make_players(self, count: int, active: int) -> dict:
        players = {}
        for i in range(active):
            players[str(i)] = {"status": "Active"}
        for i in range(active, count):
            players[str(i)] = {"status": "Inactive"}
        return players

    def test_raises_when_nfl_state_unavailable(self, stats_refresher_handler):
        with patch.object(
            stats_refresher_handler, "fetch_nfl_state", return_value=None
        ):
            with pytest.raises(RuntimeError, match="Failed to fetch NFL state"):
                stats_refresher_handler.lambda_handler({}, MagicMock())

    def test_skips_when_off_season(self, stats_refresher_handler):
        mock_s3 = MagicMock()
        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "off", "season": "2024"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
        ):
            stats_refresher_handler.lambda_handler({}, MagicMock())
        mock_s3.put_object.assert_not_called()

    def test_fetches_and_writes_all_active_players(self, stats_refresher_handler):
        players = self._make_players(count=5, active=3)
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler,
                "fetch_stats",
                return_value={"pass_yd": 100},
            ),
        ):
            stats_refresher_handler.lambda_handler({}, MagicMock())

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Key"] == "player-stats/sleeper_nfl_player_stats.json"
        written = json.loads(call_kwargs["Body"])
        assert len(written) == 3

    def test_excludes_players_with_no_stats(self, stats_refresher_handler):
        players = {"p1": {"status": "Active"}, "p2": {"status": "Active"}}
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        def fetch_side_effect(player_id, season):
            return None if player_id == "p2" else {"pass_yd": 100}

        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler, "fetch_stats", side_effect=fetch_side_effect
            ),
        ):
            stats_refresher_handler.lambda_handler({}, MagicMock())

        written = json.loads(mock_s3.put_object.call_args[1]["Body"])
        assert "p1" in written
        assert "p2" not in written

    def test_no_active_players_writes_empty_stats(self, stats_refresher_handler):
        players = self._make_players(count=5, active=0)
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler, "fetch_stats", return_value={"pass_yd": 100}
            ),
        ):
            stats_refresher_handler.lambda_handler({}, MagicMock())

        mock_s3.put_object.assert_called_once()
        written = json.loads(mock_s3.put_object.call_args[1]["Body"])
        assert written == {}

    def test_season_override_bypasses_nfl_state(self, stats_refresher_handler):
        """An explicit ``season`` in the event forces a refresh and skips the
        live NFL-state check entirely."""
        players = {"p1": {"status": "Active"}}
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}
        mock_state = MagicMock()

        with (
            patch.object(stats_refresher_handler, "fetch_nfl_state", mock_state),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler, "fetch_stats", return_value={"pass_yd": 250}
            ),
        ):
            stats_refresher_handler.lambda_handler({"season": "2025"}, MagicMock())

        mock_state.assert_not_called()
        written = json.loads(mock_s3.put_object.call_args[1]["Body"])
        assert written == {"p1": {"2025": {"pass_yd": 250}}}

    def test_season_override_refreshes_during_off_season(self, stats_refresher_handler):
        """The override still runs even when the live state would report off-season."""
        players = {"p1": {"status": "Active"}}
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "off", "season": "2026"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler, "fetch_stats", return_value={"pass_yd": 10}
            ),
        ):
            stats_refresher_handler.lambda_handler({"season": "2025"}, MagicMock())

        mock_s3.put_object.assert_called_once()
        written = json.loads(mock_s3.put_object.call_args[1]["Body"])
        assert "2025" in written["p1"]

    def test_max_players_caps_the_fan_out(self, stats_refresher_handler):
        """``max_players`` limits the run to the first N active players."""
        players = self._make_players(count=10, active=8)
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler, "fetch_stats", return_value={"pass_yd": 100}
            ) as mock_fetch,
        ):
            stats_refresher_handler.lambda_handler({"max_players": 3}, MagicMock())

        # Only the first 3 active players are fetched and written.
        assert mock_fetch.call_count == 3
        written = json.loads(mock_s3.put_object.call_args[1]["Body"])
        assert len(written) == 3

    def test_output_key_override_redirects_write(self, stats_refresher_handler):
        """``output_key`` writes to the override key, not the production cache."""
        players = {"p1": {"status": "Active"}}
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler, "fetch_stats", return_value={"pass_yd": 100}
            ),
        ):
            stats_refresher_handler.lambda_handler(
                {"output_key": "player-stats/integration-test/run.json"}, MagicMock()
            )

        assert (
            mock_s3.put_object.call_args[1]["Key"]
            == "player-stats/integration-test/run.json"
        )

    def test_defaults_to_production_key_without_override(self, stats_refresher_handler):
        """Without ``output_key`` the canonical production key is used."""
        players = {"p1": {"status": "Active"}}
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler, "fetch_stats", return_value={"pass_yd": 100}
            ),
        ):
            stats_refresher_handler.lambda_handler({}, MagicMock())

        assert (
            mock_s3.put_object.call_args[1]["Key"]
            == "player-stats/sleeper_nfl_player_stats.json"
        )

    def test_stats_keyed_by_player_and_season(self, stats_refresher_handler):
        players = {"p1": {"status": "Active"}}
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with (
            patch.object(
                stats_refresher_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_refresher_handler, "s3_client", mock_s3),
            patch.object(
                stats_refresher_handler,
                "fetch_stats",
                return_value={"pass_yd": 300},
            ),
        ):
            stats_refresher_handler.lambda_handler({}, MagicMock())

        written = json.loads(mock_s3.put_object.call_args[1]["Body"])
        assert written == {"p1": {"2024": {"pass_yd": 300}}}
