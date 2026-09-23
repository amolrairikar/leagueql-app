import asyncio
from collections.abc import Awaitable, Callable, Sequence
from functools import partial
from typing import Any

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

# Cap the response body we log on an HTTP error so a large upstream payload
# can't blow up CloudWatch volume; error bodies from the platform APIs fit well
# within this.
_MAX_LOGGED_BODY_CHARS = 2000

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
    On any HTTP error status, logs the status code and (truncated) response body
    before raising, since ``raise_for_status()`` discards the body.

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
                if response.status in retryable_statuses and attempt < max_retries:
                    logger.warning(
                        "Retryable status %s for url: %s (attempt %s/%s)",
                        response.status,
                        url,
                        attempt + 1,
                        max_retries,
                    )
                    await asyncio.sleep(base_delay * (2**attempt))
                    continue
                if response.status >= 400:
                    # Read the body before raise_for_status() discards it, so the
                    # upstream status + payload are diagnosable from the log alone.
                    body = await response.text()
                    logger.error(
                        "HTTP error for url: %s status=%s body=%s",
                        url,
                        response.status,
                        body[:_MAX_LOGGED_BODY_CHARS],
                    )
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


async def fetch_one(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    url_data: tuple[str, str, str],
    *,
    headers: dict[str, str] | None = None,
    transform: Callable[[Any, str], Any] | None = None,
) -> dict[str, Any]:
    """Fetch one ``(season, data_type, url)`` with the shared client plumbing.

    Captures the per-request scaffolding common to the ESPN and Sleeper clients: acquire the
    shared ``semaphore``, ``fetch_with_retry``, log success/failure, and shape the result as
    ``{"season", "data_type", "data"}`` (``data`` is ``None`` on any failure so
    ``validate_api_results`` flags it rather than mistaking it for a valid empty body).

    Per-platform specifics stay with the caller via two hooks: ``headers`` (request headers,
    e.g. ESPN's ``X-Fantasy-Filter``) and ``transform`` — a ``(data, data_type) -> data``
    callback applied to a *successful* body (e.g. unwrap ESPN's single-element list, normalize
    Sleeper's null preseason brackets to ``[]``).

    Args:
        session: The aiohttp session to fetch with.
        semaphore: Concurrency bound shared across the batch.
        url_data: The (season, data_type, url) tuple to fetch.
        headers: Optional request headers.
        transform: Optional post-fetch shaping of a successful body.

    Returns:
        Mapping containing season, data type, and the (possibly transformed) response body.
    """
    season, data_type, url = url_data
    async with semaphore:
        try:
            data = await fetch_with_retry(session=session, url=url, headers=headers)
            logger.info("Successfully fetched url: %s", url)
            if transform is not None:
                data = transform(data, data_type)
            return {"season": season, "data_type": data_type, "data": data}
        except Exception as e:  # noqa: BLE001 — isolate one request's failure
            logger.error("Failed request for url: %s, error: %s", url, e)
            return {"season": season, "data_type": data_type, "data": None}


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
            # A gathered BaseException signals a fetch failure, not an invalid
            # argument type, so RuntimeError (not TypeError) is correct here.
            raise RuntimeError(  # noqa: TRY004
                f"Unexpected error occurred while fetching data: {result}"
            )
        if result["data"] is None:
            raise RuntimeError(
                f"Failed to get data for season {result['season']} and data type {result['data_type']}"
            )
        validated.append(result)
    return validated
