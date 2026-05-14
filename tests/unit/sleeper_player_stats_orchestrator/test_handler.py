"""Tests for sleeper_player_stats_orchestrator/handler.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestFetchNflState:
    def test_returns_state_on_success(self, stats_orchestrator_handler):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"season_type": "regular", "season": "2024"}
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_orchestrator_handler, "http_session", mock_session):
            result = stats_orchestrator_handler.fetch_nfl_state()
        assert result == {"season_type": "regular", "season": "2024"}

    def test_returns_none_on_exception(self, stats_orchestrator_handler):
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("timeout")

        with patch.object(stats_orchestrator_handler, "http_session", mock_session):
            result = stats_orchestrator_handler.fetch_nfl_state()
        assert result is None


class TestLambdaHandlerOrchestrator:
    def _make_players(self, count: int, active: int) -> dict:
        players = {}
        for i in range(active):
            players[str(i)] = {"status": "Active"}
        for i in range(active, count):
            players[str(i)] = {"status": "Inactive"}
        return players

    def test_raises_when_nfl_state_unavailable(self, stats_orchestrator_handler):
        with patch.object(
            stats_orchestrator_handler, "fetch_nfl_state", return_value=None
        ):
            with pytest.raises(RuntimeError, match="Failed to fetch NFL state"):
                stats_orchestrator_handler.lambda_handler({}, MagicMock())

    def test_skips_when_off_season(self, stats_orchestrator_handler):
        with patch.object(
            stats_orchestrator_handler,
            "fetch_nfl_state",
            return_value={"season_type": "off", "season": "2024"},
        ):
            stats_orchestrator_handler.lambda_handler({}, MagicMock())
            # Should return without touching SQS

    def test_enqueues_active_players(self, stats_orchestrator_handler):
        players = self._make_players(count=5, active=3)
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}
        mock_sqs = MagicMock()

        with (
            patch.object(
                stats_orchestrator_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_orchestrator_handler, "s3_client", mock_s3),
            patch.object(stats_orchestrator_handler, "sqs_client", mock_sqs),
        ):
            stats_orchestrator_handler.lambda_handler({}, MagicMock())

        # 3 active players, each in one message, batched in groups of 10 -> 1 batch call
        mock_sqs.send_message_batch.assert_called_once()
        entries = mock_sqs.send_message_batch.call_args[1]["Entries"]
        assert len(entries) == 3

    def test_batches_messages_in_groups_of_10(self, stats_orchestrator_handler):
        players = self._make_players(count=25, active=25)
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}
        mock_sqs = MagicMock()

        with (
            patch.object(
                stats_orchestrator_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_orchestrator_handler, "s3_client", mock_s3),
            patch.object(stats_orchestrator_handler, "sqs_client", mock_sqs),
        ):
            stats_orchestrator_handler.lambda_handler({}, MagicMock())

        # 25 players / 10 per batch = 3 calls (10 + 10 + 5)
        assert mock_sqs.send_message_batch.call_count == 3

    def test_no_active_players_sends_no_messages(self, stats_orchestrator_handler):
        players = self._make_players(count=5, active=0)
        player_json = json.dumps(players).encode()
        mock_body = MagicMock()
        mock_body.read.return_value = player_json

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}
        mock_sqs = MagicMock()

        with (
            patch.object(
                stats_orchestrator_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(stats_orchestrator_handler, "s3_client", mock_s3),
            patch.object(stats_orchestrator_handler, "sqs_client", mock_sqs),
        ):
            stats_orchestrator_handler.lambda_handler({}, MagicMock())

        mock_sqs.send_message_batch.assert_not_called()
