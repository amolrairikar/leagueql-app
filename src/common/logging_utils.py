"""Shared JSON logging setup for all LeagueQL Lambda functions.

Vendored into every function's deployment zip via
``scripts/deployment_scripts/build_lambda_zip.sh``. A single ``correlation_id_var``
lives here so the formatter and every function that sets/reads it share one
``ContextVar`` instance; functions that never set it simply emit an empty value.
"""

import json
import logging
import time
from contextvars import ContextVar

# OpenTelemetry is only bundled with the API Lambda (backend/otel-tracing). This module is
# vendored into every function's zip, so the import is guarded — functions without
# OTel installed (Onboarder, Processor, …) simply omit ``trace_id`` from their logs.
try:
    from opentelemetry import trace as _otel_trace
except Exception:  # pragma: no cover - exercised only where OTel is absent
    _otel_trace = None

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def _active_trace_ids() -> dict[str, str]:
    """Return ``{"trace_id", "span_id"}`` for the active span, or ``{}``.

    Lets a CloudWatch log line be pivoted to its Better Stack trace and back. Empty when
    OTel is unavailable or no valid span is active (e.g. untraced invocations).
    """
    if _otel_trace is None:
        return {}
    try:
        ctx = _otel_trace.get_current_span().get_span_context()
        if not ctx.is_valid:
            return {}
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        }
    except Exception:  # tracing must never break logging
        return {}


class JsonFormatter(logging.Formatter):
    """Class to format logs in JSON format."""

    def format(self, record) -> str:
        """
        Format the log record as a JSON object.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: JSON formatted log string.
        """
        log_object = {
            "timestamp": int(time.time() * 1000),
            "level": record.levelname,
            "message": record.getMessage(),
            "function": record.funcName,
            "correlation_id": correlation_id_var.get(),
            **_active_trace_ids(),
        }
        return json.dumps(log_object)


def setup_logger() -> logging.Logger:
    """
    Set up the root logger with JSON formatted log entries.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    return logger


logger = setup_logger()
