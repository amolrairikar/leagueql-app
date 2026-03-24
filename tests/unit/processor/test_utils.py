import json
import logging
from unittest.mock import patch

from processor.utils import JsonFormatter, setup_logger


class TestJsonFormatter:
    def test_format_returns_valid_json_with_expected_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        record.funcName = "my_function"

        with patch("processor.utils.time.time", return_value=1000.0):
            result = formatter.format(record)

        parsed = json.loads(result)
        assert parsed["timestamp"] == 1000000
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert parsed["function"] == "my_function"


class TestSetupLogger:
    def test_returns_logger_with_correct_configuration(self):
        result = setup_logger()
        assert isinstance(result, logging.Logger)
        assert result.level == logging.INFO
        assert len(result.handlers) == 1
        assert isinstance(result.handlers[0], logging.StreamHandler)
        assert isinstance(result.handlers[0].formatter, JsonFormatter)
