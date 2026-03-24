from unittest.mock import MagicMock, patch


from processor.handler import lambda_handler


class TestLambdaHandler:
    def test_returns_empty_dict(self):
        with patch("processor.handler.logger"):
            result = lambda_handler({}, MagicMock())
        assert result == {}

    def test_logs_event_and_context(self):
        context = MagicMock()
        event = {"key": "value"}
        with patch("processor.handler.logger") as mock_logger:
            lambda_handler(event, context)
        assert mock_logger.info.call_count == 3
