"""Tests for the shared src/common/logging_utils.py module."""

import json
import logging

from common.logging_utils import JsonFormatter, correlation_id_var, setup_logger


def _make_record(msg="hello %s", args=("world",)):
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=msg,
        args=args,
        exc_info=None,
    )


class TestJsonFormatter:
    def test_format_returns_valid_json_with_expected_keys(self):
        formatter = JsonFormatter()
        parsed = json.loads(formatter.format(_make_record()))
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert "timestamp" in parsed
        assert "function" in parsed
        assert "correlation_id" in parsed

    def test_format_defaults_correlation_id_to_empty_string(self):
        # A context that never set the var emits an empty correlation_id.
        correlation_id_var.set("")
        formatter = JsonFormatter()
        parsed = json.loads(formatter.format(_make_record(msg="no id", args=())))
        assert parsed["correlation_id"] == ""

    def test_format_includes_set_correlation_id(self):
        token = correlation_id_var.set("abc-123")
        try:
            formatter = JsonFormatter()
            parsed = json.loads(formatter.format(_make_record(msg="x", args=())))
            assert parsed["correlation_id"] == "abc-123"
        finally:
            correlation_id_var.reset(token)


class TestSetupLogger:
    def test_returns_logger_instance(self):
        assert isinstance(setup_logger(), logging.Logger)

    def test_logger_has_handler(self):
        assert len(setup_logger().handlers) >= 1

    def test_logger_level_is_info(self):
        assert setup_logger().level == logging.INFO

    def test_handler_uses_json_formatter(self):
        logger = setup_logger()
        assert isinstance(logger.handlers[0].formatter, JsonFormatter)
