"""Tests for onboarder/utils.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest


class TestValidateApiResults:
    def test_returns_valid_results(self):
        from utils import validate_api_results

        results = [
            {"season": "2024", "data_type": "users", "data": [{"user_id": "1"}]},
            {"season": "2024", "data_type": "rosters", "data": [{"roster_id": 1}]},
        ]
        validated = validate_api_results(results)
        assert len(validated) == 2

    def test_raises_on_exception_result(self):
        from utils import validate_api_results

        results = [ValueError("something went wrong")]
        with pytest.raises(RuntimeError, match="Unexpected error"):
            validate_api_results(results)

    def test_raises_on_none_data(self):
        from utils import validate_api_results

        results = [{"season": "2024", "data_type": "users", "data": None}]
        with pytest.raises(RuntimeError, match="Failed to get data"):
            validate_api_results(results)

    def test_empty_results_returns_empty(self):
        from utils import validate_api_results

        assert validate_api_results([]) == []


class TestFetchWithRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        from utils import fetch_with_retry

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "ok"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        result = await fetch_with_retry(mock_session, "https://example.com")
        assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_retries_on_retryable_status(self):
        from utils import fetch_with_retry

        def make_response(status):
            mock_response = MagicMock()
            mock_response.status = status
            mock_response.json = AsyncMock(return_value={"data": "ok"})
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=False)
            return mock_response

        responses = [make_response(503), make_response(200)]

        mock_session = MagicMock()
        mock_session.get.side_effect = [r for r in responses]

        with patch("utils.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_with_retry(
                mock_session, "https://example.com", max_retries=2
            )

        assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_raises_on_client_error_status(self):
        from utils import fetch_with_retry

        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=404
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        with pytest.raises(aiohttp.ClientResponseError):
            await fetch_with_retry(mock_session, "https://example.com")

    @pytest.mark.asyncio
    async def test_retries_on_client_connection_error_then_succeeds(self):
        from utils import fetch_with_retry

        good_response = MagicMock()
        good_response.status = 200
        good_response.json = AsyncMock(return_value={"data": "ok"})
        good_response.__aenter__ = AsyncMock(return_value=good_response)
        good_response.__aexit__ = AsyncMock(return_value=False)

        call_count = 0

        def get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise aiohttp.ClientConnectionError("connection refused")
            return good_response

        mock_session = MagicMock()
        mock_session.get.side_effect = get_side_effect

        with patch("utils.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_with_retry(
                mock_session, "https://example.com", max_retries=2
            )

        assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_reraises_on_final_client_connection_error(self):
        from utils import fetch_with_retry

        mock_session = MagicMock()
        mock_session.get.side_effect = aiohttp.ClientConnectionError("refused")

        with patch("utils.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(aiohttp.ClientConnectionError):
                await fetch_with_retry(
                    mock_session, "https://example.com", max_retries=1
                )
