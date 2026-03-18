import json
import logging
import time
from typing import Any, Sequence, Union


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


def process_api_results(
    results: Sequence[Union[dict[str, Any], BaseException]],
) -> Sequence[dict[str, Any]]:
    """
    Groups API responses by season for simpler processing.

    Args:
        results: Unprocessed API responses

    Returns:
        Processed API responses grouped by season.
    """
    processed_results = []
    for result in results:
        if isinstance(result, BaseException):
            logger.error("Unhandled exception in gather: %s", result)
            raise RuntimeError(
                f"Unexpected error occurred while fetching ESPN data: {result}"
            )

        season = result["season"]
        data_type = result["data_type"]
        data = result["data"]

        if data is None:
            raise RuntimeError(
                f"Failed to get data for season {season} and data type {data_type}"
            )

        processed_results.append(result)

    return processed_results
