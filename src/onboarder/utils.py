import asyncio
import json
import logging
import time
from contextvars import ContextVar
from typing import Any, Sequence

import aiohttp

V2_CUTOFF = 2018
EXTENDED_SEASON_CUTOFF = 2021

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
    logger = logging.getLogger("leagueql")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    if not logger.handlers:
        logger.addHandler(handler)
    return logger


logger = setup_logger()


async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict[str, str] | None = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """
    Fetch a URL with exponential backoff retry on transient failures.

    Retries on connection errors, timeouts, and retryable HTTP status codes
    (429, 500, 502, 503, 504). Raises immediately on permanent client errors (4xx).

    Args:
        session: aiohttp client session to use for the request.
        url: The URL to fetch.
        headers: Optional HTTP headers to include in the request.
        max_retries: Maximum number of retry attempts after the initial try.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        Parsed JSON response body.
    """
    retryable_statuses = {429, 500, 502, 503, 504}
    for attempt in range(max_retries + 1):
        try:
            async with session.get(url=url, headers=headers or {}) as response:
                if response.status in retryable_statuses:
                    if attempt < max_retries:
                        logger.warning(
                            "Retryable status %s for url: %s (attempt %s/%s)",
                            response.status,
                            url,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(base_delay * (2**attempt))
                        continue
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
            if attempt == max_retries:
                raise
            logger.warning(
                "Transient error for url: %s (attempt %s/%s): %s",
                url,
                attempt + 1,
                max_retries,
                e,
            )
            await asyncio.sleep(base_delay * (2**attempt))
    raise RuntimeError(f"Exhausted retries for {url}")


def validate_api_results(
    results: Sequence[dict[str, Any] | BaseException],
) -> list[dict[str, Any]]:
    """
    Validates raw asyncio.gather results, raising on any exception or None data.

    Args:
        results: Raw results from asyncio.gather, which may include BaseException instances.

    Returns:
        List of validated result dicts, guaranteed to have non-None data fields.
    """
    validated = []
    for result in results:
        if isinstance(result, BaseException):
            logger.error("Unhandled exception in gather: %s", result)
            raise RuntimeError(
                f"Unexpected error occurred while fetching data: {result}"
            )
        if result["data"] is None:
            raise RuntimeError(
                f"Failed to get data for season {result['season']} and data type {result['data_type']}"
            )
        validated.append(result)
    return validated
