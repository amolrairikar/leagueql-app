import json
import logging
import os
import time
from contextvars import ContextVar

import boto3

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


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
        }
        return json.dumps(log_object)


def setup_logger() -> logging.Logger:
    """
    Set up the logger with JSON formatted log entries.

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

_sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
_sns_client = boto3.client("sns") if _sns_topic_arn else None


def publish_failure(error_message: str) -> None:
    if not _sns_client:
        return
    try:
        _sns_client.publish(
            TopicArn=_sns_topic_arn,
            Subject="LeagueQL Processor Failure",
            Message=f"Correlation ID: {correlation_id_var.get()}\nError: {error_message}",
        )
    except Exception:
        logger.warning("Failed to publish SNS failure notification", exc_info=True)
