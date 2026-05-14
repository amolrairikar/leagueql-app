"""Tests for onboarder/sleeper_client.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests


class TestConstructRequestUrl:
    def _make_client(self):
        from sleeper_client import SleeperClient

        with patch.object(
            SleeperClient, "_get_league_seasons", return_value={"2024": "league-123"}
        ):
            return SleeperClient(league_id="league-123")

    @pytest.mark.parametrize(
        "data_type,expected_fragment",
        [
            ("users", "/users"),
            ("rosters", "/rosters"),
            ("playoff_bracket", "/winners_bracket"),
            ("losers_bracket", "/losers_bracket"),
            ("drafts", "/drafts"),
            ("league_settings", "league/league-123"),
        ],
    )
    def test_constructs_url_for_data_type(self, data_type, expected_fragment):
        client = self._make_client()
        url = client._construct_request_url("league-123", data_type)
        assert expected_fragment in url

    def test_matchups_includes_week(self):
        client = self._make_client()
        url = client._construct_request_url("league-123", "matchups", week=7)
        assert "/matchups/7" in url

    def test_transactions_includes_week(self):
        client = self._make_client()
        url = client._construct_request_url("league-123", "transactions", week=3)
        assert "/transactions/3" in url

    def test_invalid_type_raises(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="Invalid data_type"):
            client._construct_request_url("league-123", "bad_type")


class TestBuildDraftPickUrls:
    def _make_client(self):
        from sleeper_client import SleeperClient

        with patch.object(
            SleeperClient, "_get_league_seasons", return_value={"2024": "league-123"}
        ):
            return SleeperClient(league_id="league-123")

    def test_returns_pick_urls_for_each_draft(self):
        client = self._make_client()
        results = [
            {
                "season": "2024",
                "data_type": "drafts",
                "data": [{"draft_id": "draft-abc"}, {"draft_id": "draft-xyz"}],
            }
        ]
        urls = client._build_draft_pick_urls(results)
        assert len(urls) == 2
        assert all(u[1] == "draft_picks" for u in urls)
        assert any("draft-abc" in u[2] for u in urls)

    def test_ignores_non_draft_results(self):
        client = self._make_client()
        results = [{"season": "2024", "data_type": "users", "data": [{"user_id": "1"}]}]
        urls = client._build_draft_pick_urls(results)
        assert urls == []

    def test_handles_empty_drafts_data(self):
        client = self._make_client()
        results = [{"season": "2024", "data_type": "drafts", "data": []}]
        urls = client._build_draft_pick_urls(results)
        assert urls == []

    def test_skips_draft_without_draft_id(self):
        client = self._make_client()
        results = [
            {"season": "2024", "data_type": "drafts", "data": [{"some_other": "field"}]}
        ]
        urls = client._build_draft_pick_urls(results)
        assert urls == []


class TestGetSeasons:
    def test_returns_list_of_season_keys(self):
        from sleeper_client import SleeperClient

        with patch.object(
            SleeperClient,
            "_get_league_seasons",
            return_value={"2022": "id-1", "2023": "id-2", "2024": "id-3"},
        ):
            client = SleeperClient(league_id="id-3")

        seasons = client.get_seasons()
        assert set(seasons) == {"2022", "2023", "2024"}


class TestGetLeagueSeasons:
    def test_stops_at_previous_league_id_zero(self):
        from sleeper_client import SleeperClient

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "season": "2024",
            "league_id": "league-123",
            "previous_league_id": "0",
        }

        with patch("sleeper_client.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            client = SleeperClient(league_id="league-123")

        assert client.season_mapping == {"2024": "league-123"}

    def test_refresh_mode_fetches_only_current_season(self):
        from sleeper_client import SleeperClient

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "season": "2024",
            "league_id": "league-123",
            "previous_league_id": "old-id",
        }

        with patch("sleeper_client.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            client = SleeperClient(league_id="league-123", is_refresh=True)

        assert "2024" in client.season_mapping
        assert mock_requests.get.call_count == 1

    def test_raises_on_http_error(self):
        from sleeper_client import SleeperClient

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404"
        )

        with patch("sleeper_client.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            mock_requests.exceptions.HTTPError = requests.exceptions.HTTPError
            with pytest.raises(requests.exceptions.HTTPError):
                SleeperClient(league_id="bad-id")


class TestGetLeagueSeasonsExtended:
    def test_traverses_multiple_seasons(self):
        from sleeper_client import SleeperClient

        resp1 = MagicMock()
        resp1.raise_for_status = MagicMock()
        resp1.json.return_value = {
            "season": "2024",
            "league_id": "id-2024",
            "previous_league_id": "id-2023",
        }
        resp2 = MagicMock()
        resp2.raise_for_status = MagicMock()
        resp2.json.return_value = {
            "season": "2023",
            "league_id": "id-2023",
            "previous_league_id": "0",
        }

        with patch("sleeper_client.requests") as mock_requests:
            mock_requests.get.side_effect = [resp1, resp2]
            client = SleeperClient(league_id="id-2024")

        assert client.season_mapping == {"2024": "id-2024", "2023": "id-2023"}

    def test_raises_on_max_chain_depth(self):
        from sleeper_client import SleeperClient

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "season": "2024",
            "league_id": "id-2024",
            "previous_league_id": "id-old",
        }

        with (
            patch("sleeper_client.requests") as mock_requests,
            patch("sleeper_client.MAX_CHAIN_DEPTH", 1),
        ):
            mock_requests.get.return_value = mock_response
            with pytest.raises(RuntimeError, match="Exceeded maximum chain depth"):
                SleeperClient(league_id="id-2024")

    def test_raises_runtime_error_on_missing_league_id_field(self):
        from sleeper_client import SleeperClient

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"season": "2024"}

        with patch("sleeper_client.requests") as mock_requests:
            mock_requests.get.return_value = mock_response
            with pytest.raises(
                RuntimeError, match="Unexpected response from Sleeper API"
            ):
                SleeperClient(league_id="id-2024")


class TestFetchAllSleeper:
    @pytest.mark.asyncio
    async def test_fetch_all_with_empty_urls(self):
        from sleeper_client import SleeperClient

        with patch.object(
            SleeperClient, "_get_league_seasons", return_value={"2024": "league-123"}
        ):
            client = SleeperClient(league_id="league-123")
        client.request_urls = []

        with (
            patch("sleeper_client.aiohttp.ClientSession") as mock_cls,
            patch("sleeper_client.validate_api_results", return_value=[]),
            patch.object(client, "_build_draft_pick_urls", return_value=[]),
        ):
            mock_sess = MagicMock()
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_sess

            results = await client.fetch_all()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_all_appends_draft_pick_results(self):
        from sleeper_client import SleeperClient

        with patch.object(
            SleeperClient, "_get_league_seasons", return_value={"2024": "league-123"}
        ):
            client = SleeperClient(league_id="league-123")
        client.request_urls = []

        draft_result = {"season": "2024", "data_type": "draft_picks", "data": []}

        with (
            patch("sleeper_client.aiohttp.ClientSession") as mock_cls,
            patch(
                "sleeper_client.validate_api_results", side_effect=[[], [draft_result]]
            ),
            patch.object(
                client,
                "_build_draft_pick_urls",
                return_value=[("2024", "draft_picks", "https://url")],
            ),
            patch.object(client, "_fetch", return_value=draft_result),
        ):
            mock_sess = MagicMock()
            mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
            mock_sess.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_sess

            results = await client.fetch_all()

        assert len(results) == 1
        assert results[0]["data_type"] == "draft_picks"


class TestFetchSleeper:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        import asyncio
        from unittest.mock import AsyncMock
        from sleeper_client import SleeperClient

        with patch.object(
            SleeperClient, "_get_league_seasons", return_value={"2024": "league-123"}
        ):
            client = SleeperClient(league_id="league-123")

        mock_session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        with patch(
            "sleeper_client.fetch_with_retry",
            new_callable=AsyncMock,
            return_value=[{"user_id": "1"}],
        ):
            result = await client._fetch(
                session=mock_session,
                semaphore=semaphore,
                url_data=("2024", "users", "https://example.com"),
            )

        assert result["season"] == "2024"
        assert result["data_type"] == "users"
        assert result["data"] == [{"user_id": "1"}]

    @pytest.mark.asyncio
    async def test_returns_none_data_on_exception(self):
        import asyncio
        from unittest.mock import AsyncMock
        from sleeper_client import SleeperClient

        with patch.object(
            SleeperClient, "_get_league_seasons", return_value={"2024": "league-123"}
        ):
            client = SleeperClient(league_id="league-123")

        mock_session = MagicMock()
        semaphore = asyncio.Semaphore(1)

        with patch(
            "sleeper_client.fetch_with_retry",
            new_callable=AsyncMock,
            side_effect=Exception("network fail"),
        ):
            result = await client._fetch(
                session=mock_session,
                semaphore=semaphore,
                url_data=("2024", "users", "https://example.com"),
            )

        assert result["data"] is None
        assert result["season"] == "2024"


class TestResolveSleeperCanonicalLeagueId:
    def test_resolves_via_previous_league_id_chain(self):
        from sleeper_client import resolve_sleeper_canonical_league_id

        league_response = MagicMock()
        league_response.raise_for_status = MagicMock()
        league_response.json.return_value = {
            "league_id": "new-123",
            "previous_league_id": "old-456",
        }

        ddb_item = {"canonical_league_id": {"S": "canon-abc"}}

        with (
            patch("sleeper_client.requests") as mock_requests,
            patch("sleeper_client._dynamodb") as mock_ddb,
            patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"}),
        ):
            mock_requests.get.return_value = league_response
            mock_ddb.get_item.return_value = {"Item": ddb_item}

            result = resolve_sleeper_canonical_league_id("new-123")

        assert result == "canon-abc"

    def test_returns_none_when_chain_exhausted(self):
        from sleeper_client import resolve_sleeper_canonical_league_id

        league_response = MagicMock()
        league_response.raise_for_status = MagicMock()
        league_response.json.return_value = {
            "league_id": "new-123",
            "previous_league_id": "0",
        }

        with (
            patch("sleeper_client.requests") as mock_requests,
            patch("sleeper_client._dynamodb"),
            patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"}),
        ):
            mock_requests.get.return_value = league_response
            result = resolve_sleeper_canonical_league_id("new-123")

        assert result is None

    def test_raises_on_max_chain_depth(self):
        from sleeper_client import resolve_sleeper_canonical_league_id

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "league_id": "new-123",
            "previous_league_id": "old-456",
        }

        with (
            patch("sleeper_client.requests") as mock_requests,
            patch("sleeper_client._dynamodb") as mock_ddb,
            patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"}),
            patch("sleeper_client.MAX_CHAIN_DEPTH", 1),
        ):
            mock_requests.get.return_value = mock_response
            mock_ddb.get_item.return_value = {"Item": None}

            with pytest.raises(RuntimeError, match="Exceeded maximum chain depth"):
                resolve_sleeper_canonical_league_id("new-123")

    def test_raises_on_http_error_in_chain_walk(self):
        from sleeper_client import resolve_sleeper_canonical_league_id

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "503"
        )

        with (
            patch("sleeper_client.requests") as mock_requests,
            patch("sleeper_client._dynamodb"),
            patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"}),
        ):
            mock_requests.get.return_value = mock_response
            mock_requests.exceptions.HTTPError = requests.exceptions.HTTPError

            with pytest.raises(requests.exceptions.HTTPError):
                resolve_sleeper_canonical_league_id("new-123")

    def test_raises_on_dynamodb_client_error(self):
        import botocore.exceptions
        from sleeper_client import resolve_sleeper_canonical_league_id

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "league_id": "new-123",
            "previous_league_id": "old-456",
        }

        with (
            patch("sleeper_client.requests") as mock_requests,
            patch("sleeper_client._dynamodb") as mock_ddb,
            patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"}),
        ):
            mock_requests.get.return_value = mock_response
            mock_ddb.get_item.side_effect = botocore.exceptions.ClientError(
                {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
            )

            with pytest.raises(botocore.exceptions.ClientError):
                resolve_sleeper_canonical_league_id("new-123")

    def test_continues_chain_when_no_ddb_match(self):
        from sleeper_client import resolve_sleeper_canonical_league_id

        resp1 = MagicMock()
        resp1.raise_for_status = MagicMock()
        resp1.json.return_value = {
            "league_id": "new-123",
            "previous_league_id": "prev-456",
        }

        resp2 = MagicMock()
        resp2.raise_for_status = MagicMock()
        resp2.json.return_value = {"league_id": "prev-456", "previous_league_id": "0"}

        with (
            patch("sleeper_client.requests") as mock_requests,
            patch("sleeper_client._dynamodb") as mock_ddb,
            patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"}),
        ):
            mock_requests.get.side_effect = [resp1, resp2]
            mock_ddb.get_item.return_value = {}

            result = resolve_sleeper_canonical_league_id("new-123")

        assert result is None
