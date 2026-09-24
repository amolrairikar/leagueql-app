"""Tests for onboarder/utils.py.

JSON logging (``JsonFormatter`` / ``setup_logger``) is shared code now exercised by
``tests/unit/common/test_logging_utils.py``.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest


def _make_async_cm(status: int, json_data, raise_for_status=None, text_data=""):
    """Create an async context manager mock that simulates an aiohttp response."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data)
    mock_resp.text = AsyncMock(return_value=text_data)
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

        with pytest.raises(aiohttp.ClientResponseError):
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

    async def test_attaches_body_to_error_without_logging(
        self, onboarder_utils, monkeypatch
    ):
        # A 4xx must read the raw body before raise_for_status() discards it and
        # attach it to the raised error (so the batch handler can log it), without
        # emitting its own error line.
        mock_logger = MagicMock()
        monkeypatch.setattr(onboarder_utils, "logger", mock_logger)
        session = MagicMock()
        error = aiohttp.ClientResponseError(None, None)
        error.status = 404
        resp_404 = _make_async_cm(
            404, None, raise_for_status=error, text_data='{"error":"not found"}'
        )
        session.get.return_value = resp_404

        with pytest.raises(aiohttp.ClientResponseError) as excinfo:
            await onboarder_utils.fetch_with_retry(
                session=session, url="http://test.com", base_delay=0
            )

        assert excinfo.value.upstream_body == '{"error":"not found"}'
        mock_logger.error.assert_not_called()

    async def test_truncates_attached_body(self, onboarder_utils):
        session = MagicMock()
        error = aiohttp.ClientResponseError(None, None)
        error.status = 500
        long_body = "x" * (onboarder_utils._MAX_LOGGED_BODY_CHARS + 500)
        resp_500 = _make_async_cm(
            500, None, raise_for_status=error, text_data=long_body
        )
        session.get.return_value = resp_500

        with pytest.raises(aiohttp.ClientResponseError) as excinfo:
            await onboarder_utils.fetch_with_retry(
                session=session, url="http://test.com", max_retries=0, base_delay=0
            )

        assert (
            len(excinfo.value.upstream_body) == onboarder_utils._MAX_LOGGED_BODY_CHARS
        )

    async def test_success_does_not_log_error(self, onboarder_utils, monkeypatch):
        mock_logger = MagicMock()
        monkeypatch.setattr(onboarder_utils, "logger", mock_logger)
        session = MagicMock()
        session.get.return_value = _make_async_cm(200, {"key": "val"})

        result = await onboarder_utils.fetch_with_retry(
            session=session, url="http://test.com"
        )
        assert result == {"key": "val"}
        mock_logger.error.assert_not_called()

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


class TestDescribeFetchError:
    def test_http_error_with_body_includes_status_and_body(self, onboarder_utils):
        err = aiohttp.ClientResponseError(None, None)
        err.status = 401
        err.upstream_body = '{"messages":["not authorized"]}'
        msg = onboarder_utils.describe_fetch_error(err)
        assert "status=401" in msg
        assert '{"messages":["not authorized"]}' in msg

    def test_http_error_without_body_falls_back_to_repr(self, onboarder_utils):
        # A ClientResponseError that never passed through fetch_with_retry carries no
        # upstream_body, so we render its repr rather than a bare status.
        err = aiohttp.ClientResponseError(None, None)
        err.status = 401
        msg = onboarder_utils.describe_fetch_error(err)
        assert msg.startswith("error=")

    def test_non_http_error_uses_repr(self, onboarder_utils):
        msg = onboarder_utils.describe_fetch_error(RuntimeError("Exhausted retries"))
        assert msg.startswith("error=")
        assert "Exhausted retries" in msg


class TestFetchOne:
    async def test_success_returns_shaped_result(self, onboarder_utils):
        with patch.object(
            onboarder_utils, "fetch_with_retry", AsyncMock(return_value={"ok": 1})
        ):
            result = await onboarder_utils.fetch_one(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "users", "http://x"),
            )
        assert result == {"season": "2024", "data_type": "users", "data": {"ok": 1}}

    async def test_applies_transform_to_successful_body(self, onboarder_utils):
        with patch.object(
            onboarder_utils, "fetch_with_retry", AsyncMock(return_value=None)
        ):
            result = await onboarder_utils.fetch_one(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "brackets", "http://x"),
                transform=lambda data, dt: data if data is not None else [],
            )
        assert result["data"] == []

    async def test_logs_single_line_with_status_and_body_on_error(
        self, onboarder_utils, monkeypatch
    ):
        # One consolidated ERROR carrying season, data_type, status, and the body
        # attached upstream — no separate line from fetch_with_retry.
        mock_logger = MagicMock()
        monkeypatch.setattr(onboarder_utils, "logger", mock_logger)
        err = aiohttp.ClientResponseError(None, None)
        err.status = 401
        err.upstream_body = '{"messages":["not authorized"]}'
        with patch.object(
            onboarder_utils, "fetch_with_retry", AsyncMock(side_effect=err)
        ):
            result = await onboarder_utils.fetch_one(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2023", "matchups_12", "http://x"),
            )

        assert result == {"season": "2023", "data_type": "matchups_12", "data": None}
        mock_logger.error.assert_called_once()
        args = mock_logger.error.call_args[0]
        assert args[2] == "2023"
        assert args[3] == "matchups_12"
        assert "status=401" in args[4]
        assert "not authorized" in args[4]

    async def test_logs_repr_for_non_http_failure(self, onboarder_utils, monkeypatch):
        mock_logger = MagicMock()
        monkeypatch.setattr(onboarder_utils, "logger", mock_logger)
        with patch.object(
            onboarder_utils,
            "fetch_with_retry",
            AsyncMock(side_effect=RuntimeError("Exhausted retries")),
        ):
            result = await onboarder_utils.fetch_one(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "users", "http://x"),
            )

        assert result["data"] is None
        assert "Exhausted retries" in mock_logger.error.call_args[0][4]


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
