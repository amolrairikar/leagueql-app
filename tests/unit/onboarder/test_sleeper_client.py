"""Tests for onboarder/sleeper_client.py."""

import botocore.exceptions
import pytest
import requests
from unittest.mock import MagicMock, patch


def _mock_http_response(json_data, status_code=200, raise_error=False):
    mock = MagicMock()
    mock.json.return_value = json_data
    if raise_error:
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError("err")
    else:
        mock.raise_for_status = MagicMock()
    return mock


class TestResolveSleeperCanonicalLeagueId:
    def test_found_in_dynamodb(self, onboarder_sleeper_client, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({"previous_league_id": "prev-1"})
        ddb_result = {"Item": {"canonical_league_id": {"S": "canonical-abc"}}}

        with (
            patch("requests.get", return_value=http_resp),
            patch.object(
                onboarder_sleeper_client._dynamodb, "get_item", return_value=ddb_result
            ),
        ):
            result = onboarder_sleeper_client.resolve_sleeper_canonical_league_id(
                "new-1"
            )

        assert result == "canonical-abc"

    def test_chain_exhausted_returns_none(self, onboarder_sleeper_client, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({"previous_league_id": "0"})
        with patch("requests.get", return_value=http_resp):
            result = onboarder_sleeper_client.resolve_sleeper_canonical_league_id(
                "new-1"
            )
        assert result is None

    def test_chain_exhausted_on_null_previous_league_id_returns_none(
        self, onboarder_sleeper_client, monkeypatch
    ):
        # Founding season returns JSON null for previous_league_id; the resolver must
        # treat it as end-of-chain rather than walking into league "None".
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({"previous_league_id": None})
        with patch("requests.get", return_value=http_resp) as mock_get:
            result = onboarder_sleeper_client.resolve_sleeper_canonical_league_id(
                "new-1"
            )
        assert result is None
        assert mock_get.call_count == 1

    def test_http_error_raises(self, onboarder_sleeper_client, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({}, raise_error=True)
        with patch("requests.get", return_value=http_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                onboarder_sleeper_client.resolve_sleeper_canonical_league_id("new-1")

    def test_dynamodb_client_error_raises(self, onboarder_sleeper_client, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_resp = _mock_http_response({"previous_league_id": "prev-1"})
        with (
            patch("requests.get", return_value=http_resp),
            patch.object(
                onboarder_sleeper_client._dynamodb,
                "get_item",
                side_effect=botocore.exceptions.ClientError(
                    {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
                ),
            ),
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                onboarder_sleeper_client.resolve_sleeper_canonical_league_id("new-1")

    def test_item_without_canonical_id_continues_chain(
        self, onboarder_sleeper_client, monkeypatch
    ):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        http_responses = [
            _mock_http_response({"previous_league_id": "prev-1"}),
            _mock_http_response({"previous_league_id": "0"}),
        ]
        ddb_result_no_canonical = {"Item": {}}
        with (
            patch("requests.get", side_effect=http_responses),
            patch.object(
                onboarder_sleeper_client._dynamodb,
                "get_item",
                return_value=ddb_result_no_canonical,
            ),
        ):
            result = onboarder_sleeper_client.resolve_sleeper_canonical_league_id(
                "new-1"
            )
        assert result is None


class TestSleeperClientGetLeagueSeasons:
    def test_single_season_when_is_refresh(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "league-2024", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient(
                "league-2024", is_refresh=True
            )
        assert list(client.season_mapping.keys()) == ["2024"]

    def test_walks_chain_for_all_seasons(self, onboarder_sleeper_client):
        responses = [
            _mock_http_response(
                {
                    "season": "2024",
                    "league_id": "league-2024",
                    "previous_league_id": "league-2023",
                }
            ),
            _mock_http_response(
                {
                    "season": "2023",
                    "league_id": "league-2023",
                    "previous_league_id": "0",
                }
            ),
        ]
        with patch("requests.get", side_effect=responses):
            client = onboarder_sleeper_client.SleeperClient("league-2024")
        assert "2023" in client.season_mapping
        assert "2024" in client.season_mapping

    def test_walks_chain_terminating_on_null_previous_league_id(
        self, onboarder_sleeper_client
    ):
        # The founding season is created fresh, so Sleeper returns JSON null (None) for
        # previous_league_id rather than the string "0". The walk must stop there
        # instead of trying to fetch league "None".
        responses = [
            _mock_http_response(
                {
                    "season": "2024",
                    "league_id": "league-2024",
                    "previous_league_id": "league-2023",
                }
            ),
            _mock_http_response(
                {
                    "season": "2023",
                    "league_id": "league-2023",
                    "previous_league_id": None,
                }
            ),
        ]
        with patch("requests.get", side_effect=responses) as mock_get:
            client = onboarder_sleeper_client.SleeperClient("league-2024")
        assert list(client.season_mapping.keys()) == ["2024", "2023"]
        # Exactly two fetches: no attempt to fetch league "None".
        assert mock_get.call_count == 2

    @pytest.mark.parametrize("status", ["pre_draft", "drafting"])
    def test_skips_not_started_latest_season_on_refresh(
        self, onboarder_sleeper_client, status
    ):
        # A renewed offseason season the user refreshes into is still pre_draft/
        # drafting; with is_refresh only that latest season is examined, so the
        # mapping comes back empty (nothing usable to refresh).
        http_resp = _mock_http_response(
            {
                "season": "2026",
                "league_id": "league-2026",
                "previous_league_id": "league-2025",
                "status": status,
            }
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient(
                "league-2026", is_refresh=True
            )
        assert client.season_mapping == {}

    def test_skips_not_started_season_in_full_chain(self, onboarder_sleeper_client):
        # Onboarding walks the full chain: the latest (2026) season is pre_draft and
        # must be dropped, while the started 2025 season is kept.
        responses = [
            _mock_http_response(
                {
                    "season": "2026",
                    "league_id": "league-2026",
                    "previous_league_id": "league-2025",
                    "status": "pre_draft",
                }
            ),
            _mock_http_response(
                {
                    "season": "2025",
                    "league_id": "league-2025",
                    "previous_league_id": "0",
                    "status": "complete",
                }
            ),
        ]
        with patch("requests.get", side_effect=responses):
            client = onboarder_sleeper_client.SleeperClient("league-2026")
        assert list(client.season_mapping.keys()) == ["2025"]

    def test_unknown_status_is_kept(self, onboarder_sleeper_client):
        # Defensive: an unrecognized/absent status is treated as started so a future
        # Sleeper status value never silently drops a real season.
        http_resp = _mock_http_response(
            {
                "season": "2024",
                "league_id": "league-2024",
                "previous_league_id": "0",
                "status": "some_future_status",
            }
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("league-2024")
        assert list(client.season_mapping.keys()) == ["2024"]

    def test_http_error_raises(self, onboarder_sleeper_client):
        http_resp = _mock_http_response({}, raise_error=True)
        with patch("requests.get", return_value=http_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                onboarder_sleeper_client.SleeperClient("league-2024")

    def test_missing_league_id_raises_runtime_error(self, onboarder_sleeper_client):
        http_resp = _mock_http_response({"season": "2024"})
        with patch("requests.get", return_value=http_resp):
            with pytest.raises(RuntimeError, match="missing field"):
                onboarder_sleeper_client.SleeperClient("league-2024")

    def test_chain_depth_limit_raises(self, onboarder_sleeper_client):
        # previous_league_id never reaches "0", so the shared chain walk must bail
        # out once MAX_CHAIN_DEPTH is exceeded rather than loop forever.
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "lg-prev"}
        )
        with patch("requests.get", return_value=http_resp):
            with pytest.raises(RuntimeError, match="maximum chain depth"):
                onboarder_sleeper_client.SleeperClient("lg")


class TestSleeperClientGetSeasons:
    def test_get_seasons_returns_keys(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "league-2024", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("league-2024")
        seasons = client.get_seasons()
        assert "2024" in seasons


class TestSleeperClientConstructRequestUrl:
    def _make_client(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            return onboarder_sleeper_client.SleeperClient("lg")

    def test_users_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "users")
        assert "/users" in url

    def test_rosters_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "rosters")
        assert "/rosters" in url

    def test_matchups_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "matchups", week=5)
        assert "/matchups/5" in url

    def test_playoff_bracket_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "playoff_bracket")
        assert "winners_bracket" in url

    def test_losers_bracket_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "losers_bracket")
        assert "losers_bracket" in url

    def test_transactions_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "transactions", week=3)
        assert "/transactions/3" in url

    def test_drafts_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "drafts")
        assert "/drafts" in url

    def test_league_settings_url(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        url = client._construct_request_url("lg", "league_settings")
        assert url.endswith("/league/lg")

    def test_invalid_data_type_raises(self, onboarder_sleeper_client):
        client = self._make_client(onboarder_sleeper_client)
        with pytest.raises(ValueError):
            client._construct_request_url("lg", "bogus")


class TestSleeperClientBuildAllRequestUrls:
    def test_extended_season_has_18_matchup_weeks(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2021", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")
        matchup_urls = [u for u in client.request_urls if "matchups" in u[1]]
        assert len(matchup_urls) == 18

    def test_pre_extended_season_has_17_matchup_weeks(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2020", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")
        matchup_urls = [u for u in client.request_urls if "matchups" in u[1]]
        assert len(matchup_urls) == 17


class TestSleeperClientBuildDraftPickUrls:
    def test_builds_urls_from_draft_results(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")

        results = [
            {"data_type": "drafts", "season": "2024", "data": [{"draft_id": "d1"}]},
            {"data_type": "users", "season": "2024", "data": []},
        ]
        urls = client._build_draft_pick_urls(results)
        assert len(urls) == 1
        assert "/draft/d1/picks" in urls[0][2]

    def test_skips_drafts_without_draft_id(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")

        results = [
            {"data_type": "drafts", "season": "2024", "data": [{}]},
        ]
        urls = client._build_draft_pick_urls(results)
        assert len(urls) == 0

    def test_empty_results_returns_empty(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")

        assert client._build_draft_pick_urls([]) == []


class TestResolveSleeperCanonicalLeagueIdExhaustion:
    def test_chain_iterates_without_terminal_zero_returns_none(
        self, onboarder_sleeper_client, monkeypatch
    ):
        # Patch the chain iterator to yield entries that never set previous_league_id
        # to "0" and never match a known league, so the loop runs to exhaustion and
        # falls through to the final "return None".
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")

        def fake_chain(_new_id):
            yield {"previous_league_id": "prev-1"}

        with (
            patch.object(
                onboarder_sleeper_client,
                "_iter_sleeper_league_chain",
                side_effect=fake_chain,
            ),
            patch.object(
                onboarder_sleeper_client._dynamodb,
                "get_item",
                return_value={"Item": {}},  # no canonical_league_id
            ),
        ):
            result = onboarder_sleeper_client.resolve_sleeper_canonical_league_id(
                "new-1"
            )
        assert result is None


class TestSleeperClientBuildDraftPickUrlsNonList:
    def test_non_list_draft_data_skipped(self, onboarder_sleeper_client):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            client = onboarder_sleeper_client.SleeperClient("lg")
        # drafts data that is not a list exercises the `isinstance(..., list)` guard.
        results = [{"data_type": "drafts", "season": "2024", "data": None}]
        assert client._build_draft_pick_urls(results) == []


class TestSleeperClientFetch:
    def _client(self, mod):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            return mod.SleeperClient("lg")

    async def test_fetch_returns_data(self, onboarder_sleeper_client):
        import asyncio
        from unittest.mock import AsyncMock

        client = self._client(onboarder_sleeper_client)
        with patch.object(
            onboarder_sleeper_client,
            "fetch_with_retry",
            AsyncMock(return_value=[{"user_id": "u1"}]),
        ):
            result = await client._fetch(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "users", "http://x"),
            )
        assert result == {
            "season": "2024",
            "data_type": "users",
            "data": [{"user_id": "u1"}],
        }

    async def test_fetch_returns_none_on_error(self, onboarder_sleeper_client):
        import asyncio
        from unittest.mock import AsyncMock

        client = self._client(onboarder_sleeper_client)
        with patch.object(
            onboarder_sleeper_client,
            "fetch_with_retry",
            AsyncMock(side_effect=RuntimeError("boom")),
        ):
            result = await client._fetch(
                session=MagicMock(),
                semaphore=asyncio.Semaphore(1),
                url_data=("2024", "users", "http://x"),
            )
        assert result["data"] is None


class TestSleeperClientFetchAll:
    def _client(self, mod):
        http_resp = _mock_http_response(
            {"season": "2024", "league_id": "lg", "previous_league_id": "0"}
        )
        with patch("requests.get", return_value=http_resp):
            return mod.SleeperClient("lg")

    async def test_fetch_all_fetches_draft_picks_when_present(
        self, onboarder_sleeper_client
    ):
        from unittest.mock import AsyncMock

        client = self._client(onboarder_sleeper_client)
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        session_cm.__aexit__ = AsyncMock(return_value=False)

        first_results = [
            {"season": "2024", "data_type": "drafts", "data": [{"draft_id": "d1"}]}
        ]
        pick_results = [
            {"season": "2024", "data_type": "draft_picks", "data": [{"pick": 1}]}
        ]
        mock_run = AsyncMock(side_effect=[first_results, pick_results])
        with (
            patch("aiohttp.ClientSession", return_value=session_cm),
            patch.object(onboarder_sleeper_client, "run_fetches", mock_run),
        ):
            processed = await client.fetch_all()
        data_types = {r["data_type"] for r in processed}
        assert "drafts" in data_types
        assert "draft_picks" in data_types
        assert mock_run.call_count == 2  # second call fetched the draft picks

    async def test_fetch_all_skips_draft_picks_when_absent(
        self, onboarder_sleeper_client
    ):
        from unittest.mock import AsyncMock

        client = self._client(onboarder_sleeper_client)
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        session_cm.__aexit__ = AsyncMock(return_value=False)

        results = [{"season": "2024", "data_type": "users", "data": [{"id": 1}]}]
        mock_run = AsyncMock(return_value=results)
        with (
            patch("aiohttp.ClientSession", return_value=session_cm),
            patch.object(onboarder_sleeper_client, "run_fetches", mock_run),
        ):
            processed = await client.fetch_all()
        assert processed[0]["data_type"] == "users"
        assert mock_run.call_count == 1  # no draft picks -> single fetch round
