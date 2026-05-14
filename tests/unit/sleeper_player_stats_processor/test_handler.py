"""Tests for sleeper_player_stats_processor/handler.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestFetchStats:
    def test_returns_stats_on_success(self, stats_processor_handler):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stats": {"pass_yd": 300}}
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_processor_handler, "http_session", mock_session):
            result = stats_processor_handler.fetch_stats("p1", "2024")

        assert result == {"pass_yd": 300}

    def test_returns_none_on_404(self, stats_processor_handler):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_processor_handler, "http_session", mock_session):
            result = stats_processor_handler.fetch_stats("p1", "2024")

        assert result is None

    def test_raises_on_http_error(self, stats_processor_handler):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("err")
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_processor_handler, "http_session", mock_session):
            with pytest.raises(requests.exceptions.HTTPError):
                stats_processor_handler.fetch_stats("p1", "2024")

    def test_returns_none_when_data_not_dict(self, stats_processor_handler):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [1, 2, 3]  # not a dict
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(stats_processor_handler, "http_session", mock_session):
            result = stats_processor_handler.fetch_stats("p1", "2024")

        assert result is None


class TestIsQueueDrained:
    def test_drained_when_visible_0_and_inflight_1(self, stats_processor_handler):
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {
                "ApproximateNumberOfMessages": "0",
                "ApproximateNumberOfMessagesNotVisible": "1",
            }
        }
        with patch.object(stats_processor_handler, "sqs_client", mock_sqs):
            result = stats_processor_handler.is_queue_drained("https://sqs.test/q")
        assert result is True

    def test_not_drained_when_visible_nonzero(self, stats_processor_handler):
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {
                "ApproximateNumberOfMessages": "5",
                "ApproximateNumberOfMessagesNotVisible": "1",
            }
        }
        with patch.object(stats_processor_handler, "sqs_client", mock_sqs):
            result = stats_processor_handler.is_queue_drained("https://sqs.test/q")
        assert result is False

    def test_not_drained_when_inflight_not_1(self, stats_processor_handler):
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {
                "ApproximateNumberOfMessages": "0",
                "ApproximateNumberOfMessagesNotVisible": "3",
            }
        }
        with patch.object(stats_processor_handler, "sqs_client", mock_sqs):
            result = stats_processor_handler.is_queue_drained("https://sqs.test/q")
        assert result is False


class TestCompleteSentinelExists:
    def test_returns_true_when_object_exists(self, stats_processor_handler):
        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {}
        with patch.object(stats_processor_handler, "s3_client", mock_s3):
            result = stats_processor_handler.complete_sentinel_exists("test-bucket")
        assert result is True

    def test_returns_false_when_object_missing(self, stats_processor_handler):
        class _FakeClientError(Exception):
            pass

        mock_s3 = MagicMock()
        mock_s3.exceptions.ClientError = _FakeClientError
        mock_s3.head_object.side_effect = _FakeClientError("not found")
        with patch.object(stats_processor_handler, "s3_client", mock_s3):
            result = stats_processor_handler.complete_sentinel_exists("test-bucket")
        assert result is False


class TestLambdaHandlerStatsProcessor:
    def test_processes_records_and_writes_staging(self, stats_processor_handler):
        event = {
            "Records": [
                {
                    "messageId": "msg-1",
                    "body": json.dumps({"player_id": "p1", "season": "2024"}),
                }
            ]
        }
        mock_s3 = MagicMock()
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {
                "ApproximateNumberOfMessages": "10",
                "ApproximateNumberOfMessagesNotVisible": "1",
            }
        }

        with (
            patch.object(stats_processor_handler, "s3_client", mock_s3),
            patch.object(stats_processor_handler, "sqs_client", mock_sqs),
            patch.object(
                stats_processor_handler, "fetch_stats", return_value={"pass_yd": 100}
            ),
        ):
            stats_processor_handler.lambda_handler(event, MagicMock())

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert "player-stats/staging/msg-1.json" in call_kwargs["Key"]

    def test_writes_sentinel_when_queue_drained(self, stats_processor_handler):
        class _FakeClientError(Exception):
            pass

        event = {
            "Records": [
                {
                    "messageId": "msg-1",
                    "body": json.dumps({"player_id": "p1", "season": "2024"}),
                }
            ]
        }
        mock_s3 = MagicMock()
        mock_s3.exceptions.ClientError = _FakeClientError
        mock_s3.head_object.side_effect = _FakeClientError("not found")
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {
                "ApproximateNumberOfMessages": "0",
                "ApproximateNumberOfMessagesNotVisible": "1",
            }
        }

        with (
            patch.object(stats_processor_handler, "s3_client", mock_s3),
            patch.object(stats_processor_handler, "sqs_client", mock_sqs),
            patch.object(
                stats_processor_handler, "fetch_stats", return_value={"pass_yd": 100}
            ),
        ):
            stats_processor_handler.lambda_handler(event, MagicMock())

        put_calls = mock_s3.put_object.call_args_list
        sentinel_call = next(
            (c for c in put_calls if "complete.json" in c[1]["Key"]), None
        )
        assert sentinel_call is not None

    def test_no_sentinel_when_queue_not_drained(self, stats_processor_handler):
        event = {
            "Records": [
                {
                    "messageId": "msg-1",
                    "body": json.dumps({"player_id": "p1", "season": "2024"}),
                }
            ]
        }
        mock_s3 = MagicMock()
        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {
                "ApproximateNumberOfMessages": "5",
                "ApproximateNumberOfMessagesNotVisible": "1",
            }
        }

        with (
            patch.object(stats_processor_handler, "s3_client", mock_s3),
            patch.object(stats_processor_handler, "sqs_client", mock_sqs),
            patch.object(
                stats_processor_handler, "fetch_stats", return_value={"pass_yd": 100}
            ),
        ):
            stats_processor_handler.lambda_handler(event, MagicMock())

        put_calls = mock_s3.put_object.call_args_list
        sentinel_call = next(
            (c for c in put_calls if "complete.json" in c[1]["Key"]), None
        )
        assert sentinel_call is None
