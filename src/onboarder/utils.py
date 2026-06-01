import asyncio
from functools import partial
from typing import Any, Awaitable, Callable, Sequence

import aiohttp

# Re-exported so existing ``from utils import correlation_id_var, logger`` imports
# across the onboarder package keep working.
from common.logging_utils import (  # noqa: F401
    JsonFormatter,
    correlation_id_var,
    logger,
    setup_logger,
)
from common.sns import publish_failure as _publish_failure

V2_CUTOFF = 2018
EXTENDED_SEASON_CUTOFF = 2021

publish_failure = partial(_publish_failure, subject="LeagueQL Onboarder Failure")


def matchup_weeks(season: str | int) -> range:
    """
    Return the 1-indexed week range for a season's matchups/transactions.

    Seasons from EXTENDED_SEASON_CUTOFF onward run an 18-week schedule (weeks
    1-18); earlier seasons run 17 (weeks 1-17). Shared by the ESPN and Sleeper
    clients when expanding per-week request URLs.

    Args:
        season: The season year.

    Returns:
        A range over the season's week numbers.
    """
    return range(1, 19) if int(season) >= EXTENDED_SEASON_CUTOFF else range(1, 18)


async def run_fetches(
    session: aiohttp.ClientSession,
    url_data_list: Sequence[tuple[str, str, str]],
    fetcher: Callable[..., Awaitable[dict[str, Any]]],
    concurrency: int = 10,
) -> list[dict[str, Any] | BaseException]:
    """
    Run fetches concurrently under a shared semaphore, gathering all results.

    Captures the fetch orchestration shared by the ESPN and Sleeper clients:
    bound concurrency with a semaphore and gather every result, surfacing
    exceptions rather than raising (so callers can validate them).

    Args:
        session: The aiohttp session to fetch with.
        url_data_list: (season, data_type, url) tuples to fetch.
        fetcher: Coroutine invoked as ``fetcher(session=, semaphore=, url_data=)``.
        concurrency: Maximum number of simultaneously in-flight requests.

    Returns:
        Raw ``asyncio.gather`` results (result dicts or exceptions) in input order.
    """
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        fetcher(session=session, semaphore=semaphore, url_data=url_data)
        for url_data in url_data_list
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)


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
