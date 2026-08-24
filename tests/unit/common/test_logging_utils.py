"""Tests for the shared src/common/logging_utils.py module."""

import json
import logging
from unittest.mock import MagicMock, patch

import common.logging_utils as logging_utils
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


class TestTraceContext:
    """trace_id/span_id cross-linking (backend/otel-tracing). Guarded so non-OTel Lambdas skip it."""

    def test_no_trace_keys_when_no_active_span(self):
        # OTel is installed in tests, but no span is active → keys are omitted.
        formatter = JsonFormatter()
        parsed = json.loads(formatter.format(_make_record(msg="x", args=())))
        assert "trace_id" not in parsed
        assert "span_id" not in parsed

    def test_no_trace_keys_when_otel_absent(self):
        # Simulate a Lambda zip without opentelemetry installed.
        with patch.object(logging_utils, "_otel_trace", None):
            assert logging_utils._active_trace_ids() == {}

    def test_includes_trace_and_span_id_for_active_span(self):
        ctx = MagicMock(is_valid=True, trace_id=0x1234, span_id=0xABCD)
        fake_trace = MagicMock()
        fake_trace.get_current_span.return_value.get_span_context.return_value = ctx
        with patch.object(logging_utils, "_otel_trace", fake_trace):
            parsed = json.loads(JsonFormatter().format(_make_record(msg="x", args=())))
        assert parsed["trace_id"] == format(0x1234, "032x")
        assert parsed["span_id"] == format(0xABCD, "016x")

    def test_invalid_span_context_is_skipped(self):
        ctx = MagicMock(is_valid=False)
        fake_trace = MagicMock()
        fake_trace.get_current_span.return_value.get_span_context.return_value = ctx
        with patch.object(logging_utils, "_otel_trace", fake_trace):
            assert logging_utils._active_trace_ids() == {}

    def test_trace_lookup_errors_are_swallowed(self):
        fake_trace = MagicMock()
        fake_trace.get_current_span.side_effect = RuntimeError("boom")
        with patch.object(logging_utils, "_otel_trace", fake_trace):
            assert logging_utils._active_trace_ids() == {}


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
