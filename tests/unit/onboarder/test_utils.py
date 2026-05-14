"""Tests for onboarder/utils.py."""

import json
import logging
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


class TestJsonFormatter:
    def test_format_returns_valid_json(self, onboarder_utils):
        formatter = onboarder_utils.JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        result = formatter.format(record)
        parsed = json.loads(result)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert "timestamp" in parsed
        assert "function" in parsed


class TestSetupLogger:
    def test_returns_logger_instance(self, onboarder_utils):
        logger = onboarder_utils.setup_logger()
        assert isinstance(logger, logging.Logger)

    def test_logger_has_handler(self, onboarder_utils):
        logger = onboarder_utils.setup_logger()
        assert len(logger.handlers) >= 1

    def test_logger_level_is_info(self, onboarder_utils):
        logger = onboarder_utils.setup_logger()
        assert logger.level == logging.INFO


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
