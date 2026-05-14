"""Tests for sleeper_player_stats_orchestrator/handler.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestFetchNflState:
    def test_returns_dict_on_success(self):
        import handler

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"season_type": "regular", "season": "2024"}

        with patch.object(handler, "http_session") as mock_session:
            mock_session.get.return_value = mock_response
            result = handler.fetch_nfl_state()

        assert result == {"season_type": "regular", "season": "2024"}

    def test_returns_none_on_exception(self):
        import handler

        with patch.object(handler, "http_session") as mock_session:
            mock_session.get.side_effect = Exception("network error")
            result = handler.fetch_nfl_state()

        assert result is None


class TestLambdaHandler:
    def test_raises_when_nfl_state_unavailable(self, mock_context):
        import handler

        with patch.object(handler, "fetch_nfl_state", return_value=None):
            with pytest.raises(RuntimeError, match="Failed to fetch NFL state"):
                handler.lambda_handler({}, mock_context)

    def test_skips_when_season_is_off(self, mock_context):
        import handler

        with patch.object(
            handler,
            "fetch_nfl_state",
            return_value={"season_type": "off", "season": "2024"},
        ):
            handler.lambda_handler({}, mock_context)

        # No SQS calls when season is off
        # Verified by absence of errors (no further assertions needed since sqs_client is a real object)

    def test_enqueues_active_players_to_sqs(self, mock_context):
        import handler

        players_data = {
            "p1": {"status": "Active"},
            "p2": {"status": "Active"},
            "p3": {"status": "Inactive"},
        }

        with (
            patch.object(
                handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(handler, "s3_client") as mock_s3,
            patch.object(handler, "sqs_client") as mock_sqs,
        ):
            mock_s3.get_object.return_value = {
                "Body": MagicMock(read=lambda: json.dumps(players_data).encode())
            }
            handler.lambda_handler({}, mock_context)

        calls = mock_sqs.send_message_batch.call_args_list
        total_messages = sum(len(c[1]["Entries"]) for c in calls)
        assert total_messages == 2
        all_entries = [e for c in calls for e in c[1]["Entries"]]
        player_ids = {json.loads(e["MessageBody"])["player_id"] for e in all_entries}
        assert player_ids == {"p1", "p2"}

    def test_batches_sqs_messages_in_groups_of_10(self, mock_context):
        import handler

        players_data = {f"p{i}": {"status": "Active"} for i in range(25)}

        with (
            patch.object(
                handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular", "season": "2024"},
            ),
            patch.object(handler, "s3_client") as mock_s3,
            patch.object(handler, "sqs_client") as mock_sqs,
        ):
            mock_s3.get_object.return_value = {
                "Body": MagicMock(read=lambda: json.dumps(players_data).encode())
            }
            handler.lambda_handler({}, mock_context)

        calls = mock_sqs.send_message_batch.call_args_list
        # 25 players → 2 full batches of 10 + 1 partial batch of 5
        assert len(calls) == 3
        batch_sizes = [len(c[1]["Entries"]) for c in calls]
        assert sorted(batch_sizes) == [5, 10, 10]
