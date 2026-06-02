"""Tests for onboarder/utils.py.

JSON logging (``JsonFormatter`` / ``setup_logger``) is shared code now exercised by
``tests/unit/common/test_logging_utils.py``.
"""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest


def _make_async_cm(status: int, json_data, raise_for_status=None):
    """Create an async context manager mock that simulates an aiohttp response."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data)
    if raise_for_status is not None:
        mock_resp.raise_for_status = MagicMock(side_effect=raise_for_status)
    else:
        mock_resp.raise_for_status = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestMatchupWeeks:
    def test_extended_season_has_18_weeks(self, onboarder_utils):
        assert list(onboarder_utils.matchup_weeks("2021")) == list(range(1, 19))

    def test_pre_extended_season_has_17_weeks(self, onboarder_utils):
        assert list(onboarder_utils.matchup_weeks(2020)) == list(range(1, 18))


class TestRunFetches:
    async def test_runs_all_fetchers_and_returns_results(self, onboarder_utils):
        calls = []

        async def fake_fetch(session, semaphore, url_data):
            calls.append(url_data)
            return {"season": url_data[0], "data_type": url_data[1], "data": {"ok": 1}}

        url_data_list = [("2024", "users", "u"), ("2024", "rosters", "r")]
        results = await onboarder_utils.run_fetches(
            session=MagicMock(), url_data_list=url_data_list, fetcher=fake_fetch
        )
        assert len(results) == 2
        assert {r["data_type"] for r in results} == {"users", "rosters"}
        assert len(calls) == 2

    async def test_gathers_exceptions_instead_of_raising(self, onboarder_utils):
        async def boom(session, semaphore, url_data):
            raise RuntimeError("nope")

        results = await onboarder_utils.run_fetches(
            session=MagicMock(), url_data_list=[("2024", "users", "u")], fetcher=boom
        )
        assert len(results) == 1
        assert isinstance(results[0], RuntimeError)


class TestFetchWithRetry:
    async def test_success_on_first_attempt(self, onboarder_utils):
        session = MagicMock()
        session.get.return_value = _make_async_cm(200, {"key": "val"})

        result = await onboarder_utils.fetch_with_retry(
            session=session, url="http://test.com"
        )
        assert result == {"key": "val"}

    async def test_retries_on_500_then_succeeds(self, onboarder_utils):
        session = MagicMock()
        resp_500 = _make_async_cm(
            500, None, raise_for_status=aiohttp.ClientResponseError(None, None)
        )
        resp_200 = _make_async_cm(200, {"ok": True})
        session.get.side_effect = [resp_500, resp_200]

        result = await onboarder_utils.fetch_with_retry(
            session=session, url="http://test.com", base_delay=0
        )
        assert result == {"ok": True}

    async def test_raises_after_max_retries_on_5xx(self, onboarder_utils):
        session = MagicMock()
        resp_500 = _make_async_cm(
            500, None, raise_for_status=aiohttp.ClientResponseError(None, None)
        )
        session.get.return_value = resp_500

        with pytest.raises(Exception):
            await onboarder_utils.fetch_with_retry(
                session=session, url="http://test.com", max_retries=1, base_delay=0
            )

    async def test_raises_immediately_on_4xx(self, onboarder_utils):
        session = MagicMock()
        error = aiohttp.ClientResponseError(None, None)
        error.status = 404
        resp_404 = _make_async_cm(404, None, raise_for_status=error)
        session.get.return_value = resp_404

        with pytest.raises(aiohttp.ClientResponseError):
            await onboarder_utils.fetch_with_retry(
                session=session, url="http://test.com", base_delay=0
            )

    async def test_retries_on_connection_error(self, onboarder_utils):
        session = MagicMock()
        cm_error = MagicMock()
        cm_error.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientConnectionError("conn refused")
        )
        cm_error.__aexit__ = AsyncMock(return_value=False)
        resp_200 = _make_async_cm(200, {"ok": True})
        session.get.side_effect = [cm_error, resp_200]

        result = await onboarder_utils.fetch_with_retry(
            session=session, url="http://test.com", base_delay=0
        )
        assert result == {"ok": True}

    async def test_raises_after_max_retries_on_connection_error(self, onboarder_utils):
        # Every attempt hits a connection error; the final attempt re-raises rather
        # than retrying again.
        session = MagicMock()
        cm_error = MagicMock()
        cm_error.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientConnectionError("conn refused")
        )
        cm_error.__aexit__ = AsyncMock(return_value=False)
        session.get.return_value = cm_error

        with pytest.raises(aiohttp.ClientConnectionError):
            await onboarder_utils.fetch_with_retry(
                session=session, url="http://test.com", max_retries=1, base_delay=0
            )

    async def test_raises_runtime_error_when_no_attempts(self, onboarder_utils):
        # A negative max_retries yields an empty attempt range, so the loop body
        # never runs and the exhausted-retries guard raises.
        session = MagicMock()
        with pytest.raises(RuntimeError, match="Exhausted retries"):
            await onboarder_utils.fetch_with_retry(
                session=session, url="http://test.com", max_retries=-1
            )

    async def test_passes_headers_to_request(self, onboarder_utils):
        session = MagicMock()
        session.get.return_value = _make_async_cm(200, {})

        await onboarder_utils.fetch_with_retry(
            session=session, url="http://test.com", headers={"X-Test": "1"}
        )
        call_kwargs = session.get.call_args[1]
        assert call_kwargs["headers"] == {"X-Test": "1"}


class TestValidateApiResults:
    def test_returns_valid_results(self, onboarder_utils):
        results = [
            {"season": "2024", "data_type": "users", "data": [{"id": 1}]},
        ]
        validated = onboarder_utils.validate_api_results(results)
        assert len(validated) == 1
        assert validated[0]["data"] == [{"id": 1}]

    def test_raises_on_exception_in_results(self, onboarder_utils):
        results = [RuntimeError("fetch failed")]
        with pytest.raises(RuntimeError, match="Unexpected error"):
            onboarder_utils.validate_api_results(results)

    def test_raises_when_data_is_none(self, onboarder_utils):
        results = [{"season": "2024", "data_type": "users", "data": None}]
        with pytest.raises(RuntimeError, match="Failed to get data"):
            onboarder_utils.validate_api_results(results)

    def test_raises_on_base_exception(self, onboarder_utils):
        results = [KeyError("missing")]
        with pytest.raises(RuntimeError):
            onboarder_utils.validate_api_results(results)
