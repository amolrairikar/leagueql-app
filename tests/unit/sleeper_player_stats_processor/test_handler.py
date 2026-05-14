"""Tests for sleeper_player_stats_processor/handler.py."""

import json
from unittest.mock import MagicMock, patch

import botocore.exceptions


class TestCompleteSentinelExists:
    def test_returns_true_when_object_exists(self):
        import handler

        with patch.object(handler, "s3_client") as mock_s3:
            mock_s3.head_object.return_value = {}
            assert handler.complete_sentinel_exists("my-bucket") is True

        mock_s3.head_object.assert_called_once_with(
            Bucket="my-bucket", Key="player-stats/staging/complete.json"
        )

    def test_returns_false_on_client_error(self):
        import handler

        with patch.object(handler, "s3_client") as mock_s3:
            mock_s3.exceptions.ClientError = botocore.exceptions.ClientError
            mock_s3.head_object.side_effect = botocore.exceptions.ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
            )
            assert handler.complete_sentinel_exists("my-bucket") is False


class TestFetchStats:
    def test_returns_stats_on_success(self):
        import handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"stats": {"rush_yd": 100}}

        with patch.object(handler, "http_session") as mock_session:
            mock_session.get.return_value = mock_response
            result = handler.fetch_stats("player-123", "2024")

        assert result == {"rush_yd": 100}

    def test_returns_none_on_404(self):
        import handler

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(handler, "http_session") as mock_session:
            mock_session.get.return_value = mock_response
            result = handler.fetch_stats("unknown-player", "2024")

        assert result is None

    def test_returns_none_when_response_is_not_dict(self):
        import handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = None

        with patch.object(handler, "http_session") as mock_session:
            mock_session.get.return_value = mock_response
            result = handler.fetch_stats("player-123", "2024")

        assert result is None


class TestIsQueueDrained:
    def test_returns_true_when_visible_zero_and_in_flight_one(self):
        import handler

        with patch.object(handler, "sqs_client") as mock_sqs:
            mock_sqs.get_queue_attributes.return_value = {
                "Attributes": {
                    "ApproximateNumberOfMessages": "0",
                    "ApproximateNumberOfMessagesNotVisible": "1",
                }
            }
            assert handler.is_queue_drained("https://sqs.test/queue") is True

    def test_returns_false_when_visible_not_zero(self):
        import handler

        with patch.object(handler, "sqs_client") as mock_sqs:
            mock_sqs.get_queue_attributes.return_value = {
                "Attributes": {
                    "ApproximateNumberOfMessages": "5",
                    "ApproximateNumberOfMessagesNotVisible": "1",
                }
            }
            assert handler.is_queue_drained("https://sqs.test/queue") is False

    def test_returns_false_when_in_flight_not_one(self):
        import handler

        with patch.object(handler, "sqs_client") as mock_sqs:
            mock_sqs.get_queue_attributes.return_value = {
                "Attributes": {
                    "ApproximateNumberOfMessages": "0",
                    "ApproximateNumberOfMessagesNotVisible": "3",
                }
            }
            assert handler.is_queue_drained("https://sqs.test/queue") is False


class TestLambdaHandler:
    def test_processes_records_and_writes_staging(self, mock_context):
        import handler

        event = {
            "Records": [
                {
                    "body": json.dumps({"player_id": "p1", "season": "2024"}),
                    "messageId": "msg-001",
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"stats": {"rush_yd": 50}}

        with (
            patch.object(handler, "http_session") as mock_session,
            patch.object(handler, "s3_client") as mock_s3,
            patch.object(handler, "is_queue_drained", return_value=False),
        ):
            mock_session.get.return_value = mock_response
            handler.lambda_handler(event, mock_context)

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert "player-stats/staging/msg-001.json" == call_kwargs["Key"]
        body = json.loads(call_kwargs["Body"])
        assert "p1" in body

    def test_writes_sentinel_when_queue_drained(self, mock_context):
        import handler

        event = {
            "Records": [
                {
                    "body": json.dumps({"player_id": "p1", "season": "2024"}),
                    "messageId": "msg-001",
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"stats": {}}

        with (
            patch.object(handler, "http_session") as mock_session,
            patch.object(handler, "s3_client") as mock_s3,
            patch.object(handler, "is_queue_drained", return_value=True),
            patch.object(handler, "complete_sentinel_exists", return_value=False),
        ):
            mock_session.get.return_value = mock_response
            handler.lambda_handler(event, mock_context)

        put_calls = mock_s3.put_object.call_args_list
        keys = [c[1]["Key"] for c in put_calls]
        assert "player-stats/staging/complete.json" in keys

    def test_no_sentinel_when_queue_not_drained(self, mock_context):
        import handler

        event = {
            "Records": [
                {
                    "body": json.dumps({"player_id": "p1", "season": "2024"}),
                    "messageId": "msg-001",
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"stats": {}}

        with (
            patch.object(handler, "http_session") as mock_session,
            patch.object(handler, "s3_client") as mock_s3,
            patch.object(handler, "is_queue_drained", return_value=False),
        ):
            mock_session.get.return_value = mock_response
            handler.lambda_handler(event, mock_context)

        put_calls = mock_s3.put_object.call_args_list
        keys = [c[1]["Key"] for c in put_calls]
        assert "player-stats/staging/complete.json" not in keys
