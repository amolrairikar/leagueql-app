"""Tests for sleeper_refresh/utils.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestGetNflState:
    def test_returns_nfl_state_on_success(self, sleeper_refresh_utils):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"season_type": "regular", "week": 5}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            result = sleeper_refresh_utils.get_nfl_state()
        assert result == {"season_type": "regular", "week": 5}

    def test_raises_on_http_error(self, sleeper_refresh_utils):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("err")
        with (
            patch("requests.get", return_value=mock_resp),
            pytest.raises(requests.exceptions.HTTPError),
        ):
            sleeper_refresh_utils.get_nfl_state()


class TestGetSleeperLeagues:
    def test_returns_most_recent_league_id_per_canonical(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "canonical-abc"},
                    "league_id": {"S": "lg-2024"},
                    "seasons": {"SS": ["2023", "2024"]},
                },
                {
                    "canonical_league_id": {"S": "canonical-abc"},
                    "league_id": {"S": "lg-2023"},
                    "seasons": {"SS": ["2023"]},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2024)
        assert result == [
            {"league_id": "lg-2024", "canonical_league_id": "canonical-abc"}
        ]

    def test_handles_pagination(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = [
            {
                "Items": [
                    {
                        "canonical_league_id": {"S": "c1"},
                        "league_id": {"S": "lg1"},
                        "seasons": {"SS": ["2024"]},
                    }
                ],
                "LastEvaluatedKey": {"PK": "x"},
            },
            {
                "Items": [
                    {
                        "canonical_league_id": {"S": "c2"},
                        "league_id": {"S": "lg2"},
                        "seasons": {"SS": ["2024"]},
                    }
                ]
            },
        ]
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2024)
        assert len(result) == 2
        assert all("league_id" in r and "canonical_league_id" in r for r in result)
        assert mock_ddb.query.call_count == 2

    def test_returns_empty_list_when_no_items(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {"Items": []}
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2024)
        assert result == []

    def test_skips_items_with_missing_fields(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {"canonical_league_id": {"S": "c1"}},  # missing league_id and seasons
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2024)
        assert result == []

    def test_includes_pending_renewal_alongside_current_season(
        self, sleeper_refresh_utils
    ):
        # A league mid-renewal: the current season's lookup (with seasons) plus a pending
        # lookup for the not-yet-started season (pending_season marker, no seasons). Both
        # league IDs must be refreshed so the pending season attaches once it starts.
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "canonical-abc"},
                    "league_id": {"S": "lg-2025"},
                    "seasons": {"SS": ["2024", "2025"]},
                },
                {
                    "canonical_league_id": {"S": "canonical-abc"},
                    "league_id": {"S": "lg-2026"},
                    "pending_season": {"S": "2026"},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2025)
        assert {r["league_id"] for r in result} == {"lg-2025", "lg-2026"}
        assert all(r["canonical_league_id"] == "canonical-abc" for r in result)

    def test_pending_lookup_excluded_from_most_recent_selection(
        self, sleeper_refresh_utils
    ):
        # A pending (season-less) lookup must never be chosen as a canonical's most
        # recent season — it is only polled as a pending extra, not as the main refresh.
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "c1"},
                    "league_id": {"S": "lg-2026"},
                    "pending_season": {"S": "2026"},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2026)
        # Only the pending poll entry, no most-recent entry (it has no real seasons yet).
        assert result == [{"league_id": "lg-2026", "canonical_league_id": "c1"}]

    def test_multiple_canonical_ids_returns_one_per(self, sleeper_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "c1"},
                    "league_id": {"S": "lg1"},
                    "seasons": {"SS": ["2024"]},
                },
                {
                    "canonical_league_id": {"S": "c2"},
                    "league_id": {"S": "lg2"},
                    "seasons": {"SS": ["2024"]},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2024)
        assert len(result) == 2

    def test_skips_league_behind_current_season(self, sleeper_refresh_utils):
        # A league onboarded only through a completed prior season (2025) is skipped
        # once the current NFL season (2026) is newer — its finished data cannot change
        # and a refresh could never discover the new season.
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "c1"},
                    "league_id": {"S": "lg-2025"},
                    "seasons": {"SS": ["2024", "2025"]},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2026)
        assert result == []

    def test_refreshes_league_at_current_season(self, sleeper_refresh_utils):
        # A league whose newest onboarded season equals the current NFL season is
        # refreshed as normal.
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "c1"},
                    "league_id": {"S": "lg-2026"},
                    "seasons": {"SS": ["2025", "2026"]},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2026)
        assert result == [{"league_id": "lg-2026", "canonical_league_id": "c1"}]

    def test_skips_stale_pending_renewal(self, sleeper_refresh_utils):
        # An abandoned pending renewal (pending_season behind the current NFL season)
        # is not polled; a current/future pending still is.
        mock_ddb = MagicMock()
        mock_ddb.query.return_value = {
            "Items": [
                {
                    "canonical_league_id": {"S": "c1"},
                    "league_id": {"S": "lg-2025-pending"},
                    "pending_season": {"S": "2025"},
                },
                {
                    "canonical_league_id": {"S": "c2"},
                    "league_id": {"S": "lg-2026-pending"},
                    "pending_season": {"S": "2026"},
                },
            ]
        }
        with patch.object(sleeper_refresh_utils, "_dynamodb_client", mock_ddb):
            result = sleeper_refresh_utils.get_sleeper_leagues(2026)
        assert result == [{"league_id": "lg-2026-pending", "canonical_league_id": "c2"}]


class TestInvokeOnboarderLambda:
    def test_invokes_lambda_successfully(self, sleeper_refresh_utils):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 202}
        with patch.object(sleeper_refresh_utils, "_lambda_client", mock_lambda):
            sleeper_refresh_utils.invoke_onboarder_lambda(
                "league-123",
                canonical_league_id="canonical-abc",
                correlation_id="test-corr-id",
            )
        mock_lambda.invoke.assert_called_once()
        payload = json.loads(mock_lambda.invoke.call_args[1]["Payload"])
        assert payload["body"]["leagueId"] == "league-123"
        assert payload["canonicalLeagueId"] == "canonical-abc"
        assert payload["requestType"] == "REFRESH"
        assert payload["correlation_id"] == "test-corr-id"

    def test_raises_when_status_not_202(self, sleeper_refresh_utils):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 500}
        with (
            patch.object(sleeper_refresh_utils, "_lambda_client", mock_lambda),
            pytest.raises(Exception, match="status code 500"),
        ):
            sleeper_refresh_utils.invoke_onboarder_lambda(
                "league-123",
                canonical_league_id="canonical-abc",
                correlation_id="test-corr-id",
            )
