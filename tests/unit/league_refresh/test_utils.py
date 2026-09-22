"""Tests for league_refresh/utils.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests


def _query_side_effect(sleeper_pages=None, yahoo_pages=None, espn_pages=None):
    """Build a ``query`` side_effect that responds per GSI2 ``platform`` partition.

    ``sleeper_pages`` / ``yahoo_pages`` / ``espn_pages`` are lists of response dicts (each may
    carry a ``LastEvaluatedKey`` to drive pagination); each platform's pages are returned in
    order across successive queries. A platform with no configured pages returns an empty page.
    """
    pages = {
        "SLEEPER": iter(sleeper_pages or [{"Items": []}]),
        "YAHOO": iter(yahoo_pages or [{"Items": []}]),
        "ESPN": iter(espn_pages or [{"Items": []}]),
    }

    def _side_effect(**kwargs):
        platform = kwargs["ExpressionAttributeValues"][":platform"]["S"]
        return next(pages[platform])

    return _side_effect


class TestGetNflState:
    def test_returns_nfl_state_on_success(self, league_refresh_utils):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"season_type": "regular", "week": 5}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            result = league_refresh_utils.get_nfl_state()
        assert result == {"season_type": "regular", "week": 5}

    def test_raises_on_http_error(self, league_refresh_utils):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("err")
        with (
            patch("requests.get", return_value=mock_resp),
            pytest.raises(requests.exceptions.HTTPError),
        ):
            league_refresh_utils.get_nfl_state()


class TestGetLeaguesToRefreshSleeper:
    def test_returns_most_recent_league_id_per_canonical(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
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
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2024)
        assert result == [
            {
                "platform": "SLEEPER",
                "league_id": "lg-2024",
                "canonical_league_id": "canonical-abc",
                "owner_user_id": None,
                "season": None,
            }
        ]

    def test_handles_pagination(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
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
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2024)
        assert len(result) == 2
        assert all(
            r["platform"] == "SLEEPER" and r["owner_user_id"] is None for r in result
        )
        # Two Sleeper pages + one (empty) Yahoo query + one (empty) ESPN query.
        assert mock_ddb.query.call_count == 4

    def test_returns_empty_list_when_no_items(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect()
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2024)
        assert result == []

    def test_skips_items_with_missing_fields(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
                    "Items": [{"canonical_league_id": {"S": "c1"}}]
                }  # no league_id/seasons
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2024)
        assert result == []

    def test_includes_pending_renewal_alongside_current_season(
        self, league_refresh_utils
    ):
        # A league mid-renewal: the current season's lookup (with seasons) plus a pending
        # lookup for the not-yet-started season (pending_season marker, no seasons). Both
        # league IDs must be refreshed so the pending season attaches once it starts.
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
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
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2025)
        assert {r["league_id"] for r in result} == {"lg-2025", "lg-2026"}
        assert all(r["canonical_league_id"] == "canonical-abc" for r in result)
        assert all(r["platform"] == "SLEEPER" for r in result)

    def test_pending_lookup_excluded_from_most_recent_selection(
        self, league_refresh_utils
    ):
        # A pending (season-less) lookup must never be chosen as a canonical's most
        # recent season — it is only polled as a pending extra, not as the main refresh.
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "c1"},
                            "league_id": {"S": "lg-2026"},
                            "pending_season": {"S": "2026"},
                        }
                    ]
                }
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == [
            {
                "platform": "SLEEPER",
                "league_id": "lg-2026",
                "canonical_league_id": "c1",
                "owner_user_id": None,
                "season": None,
            }
        ]

    def test_multiple_canonical_ids_returns_one_per(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
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
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2024)
        assert len(result) == 2

    def test_skips_league_behind_current_season(self, league_refresh_utils):
        # A league onboarded only through a completed prior season (2025) is skipped
        # once the current NFL season (2026) is newer — its finished data cannot change
        # and a refresh could never discover the new season.
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "c1"},
                            "league_id": {"S": "lg-2025"},
                            "seasons": {"SS": ["2024", "2025"]},
                        }
                    ]
                }
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == []

    def test_refreshes_league_at_current_season(self, league_refresh_utils):
        # A league whose newest onboarded season equals the current NFL season is
        # refreshed as normal.
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "c1"},
                            "league_id": {"S": "lg-2026"},
                            "seasons": {"SS": ["2025", "2026"]},
                        }
                    ]
                }
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == [
            {
                "platform": "SLEEPER",
                "league_id": "lg-2026",
                "canonical_league_id": "c1",
                "owner_user_id": None,
                "season": None,
            }
        ]

    def test_skips_stale_pending_renewal(self, league_refresh_utils):
        # An abandoned pending renewal (pending_season behind the current NFL season)
        # is not polled; a current/future pending still is.
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
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
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == [
            {
                "platform": "SLEEPER",
                "league_id": "lg-2026-pending",
                "canonical_league_id": "c2",
                "owner_user_id": None,
                "season": None,
            }
        ]


class TestGetLeaguesToRefreshYahoo:
    def test_resolves_owner_when_opted_in(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            yahoo_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "y-canon"},
                            "league_id": {"S": "y-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ]
        )
        mock_ddb.get_item.return_value = {
            "Item": {
                "owner_user_id": {"S": "user-42"},
                "auto_refresh_enabled": {"BOOL": True},
            }
        }
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == [
            {
                "platform": "YAHOO",
                "league_id": "y-2026",
                "canonical_league_id": "y-canon",
                "owner_user_id": "user-42",
                "season": None,
            }
        ]
        # METADATA point read keyed by the canonical league.
        get_key = mock_ddb.get_item.call_args.kwargs["Key"]
        assert get_key["PK"]["S"] == "LEAGUE#y-canon"
        assert get_key["SK"]["S"] == "METADATA"

    def test_skips_yahoo_league_not_opted_in(self, league_refresh_utils):
        # Owner present but auto_refresh_enabled absent/false → opt-in required, skipped.
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            yahoo_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "y-canon"},
                            "league_id": {"S": "y-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ]
        )
        mock_ddb.get_item.return_value = {"Item": {"owner_user_id": {"S": "user-42"}}}
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == []

    def test_skips_yahoo_league_without_owner(self, league_refresh_utils):
        # Opted in but no owner_user_id (e.g. system-onboarded) → skipped.
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            yahoo_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "y-canon"},
                            "league_id": {"S": "y-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ]
        )
        mock_ddb.get_item.return_value = {
            "Item": {"platform": {"S": "YAHOO"}, "auto_refresh_enabled": {"BOOL": True}}
        }
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == []

    def test_skips_yahoo_league_with_missing_metadata(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            yahoo_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "y-canon"},
                            "league_id": {"S": "y-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ]
        )
        mock_ddb.get_item.return_value = {}  # no METADATA item
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == []

    def test_yahoo_has_no_pending_renewal_polling(self, league_refresh_utils):
        # A season-less Yahoo lookup (no seasons) is not a most-recent selection and
        # Yahoo has no pending-renewal path, so nothing is refreshed and no owner is read.
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            yahoo_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "y-canon"},
                            "league_id": {"S": "y-pending"},
                            "pending_season": {"S": "2026"},
                        }
                    ]
                }
            ]
        )
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == []
        mock_ddb.get_item.assert_not_called()


class TestGetLeaguesToRefreshEspn:
    def test_selects_opted_in_espn_with_owner_and_season(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            espn_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "e-canon"},
                            "league_id": {"S": "e-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ]
        )
        mock_ddb.get_item.return_value = {
            "Item": {
                "owner_user_id": {"S": "user-7"},
                "auto_refresh_enabled": {"BOOL": True},
            }
        }
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == [
            {
                "platform": "ESPN",
                "league_id": "e-2026",
                "canonical_league_id": "e-canon",
                "owner_user_id": "user-7",
                # ESPN carries the current season (its client needs a latest season).
                "season": "2026",
            }
        ]

    def test_skips_espn_league_not_opted_in(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            espn_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "e-canon"},
                            "league_id": {"S": "e-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ]
        )
        mock_ddb.get_item.return_value = {"Item": {"owner_user_id": {"S": "user-7"}}}
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == []

    def test_skips_opted_in_espn_without_owner(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            espn_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "e-canon"},
                            "league_id": {"S": "e-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ]
        )
        mock_ddb.get_item.return_value = {
            "Item": {"auto_refresh_enabled": {"BOOL": True}}
        }
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        assert result == []


class TestGetLeaguesToRefreshAllPlatforms:
    def test_returns_all_three_platforms(self, league_refresh_utils):
        mock_ddb = MagicMock()
        mock_ddb.query.side_effect = _query_side_effect(
            sleeper_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "s-canon"},
                            "league_id": {"S": "s-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ],
            yahoo_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "y-canon"},
                            "league_id": {"S": "y-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ],
            espn_pages=[
                {
                    "Items": [
                        {
                            "canonical_league_id": {"S": "e-canon"},
                            "league_id": {"S": "e-2026"},
                            "seasons": {"SS": ["2026"]},
                        }
                    ]
                }
            ],
        )
        # Both credentialed leagues are owned + opted in.
        mock_ddb.get_item.return_value = {
            "Item": {
                "owner_user_id": {"S": "user-42"},
                "auto_refresh_enabled": {"BOOL": True},
            }
        }
        with patch.object(league_refresh_utils, "_dynamodb_client", mock_ddb):
            result = league_refresh_utils.get_leagues_to_refresh(2026)
        by_platform = {r["platform"]: r for r in result}
        assert by_platform["SLEEPER"]["owner_user_id"] is None
        assert by_platform["SLEEPER"]["season"] is None
        assert by_platform["YAHOO"]["owner_user_id"] == "user-42"
        assert by_platform["YAHOO"]["season"] is None
        assert by_platform["ESPN"]["owner_user_id"] == "user-42"
        assert by_platform["ESPN"]["season"] == "2026"


class TestPacing:
    def test_dispatch_sleep_seconds_bounds(self, league_refresh_utils):
        # base interval + uniform(0, jitter); with jitter drawn at its max, equals the sum.
        with patch.object(league_refresh_utils.random, "uniform", return_value=2.0):
            secs = league_refresh_utils.dispatch_sleep_seconds()
        assert secs == league_refresh_utils.DISPATCH_INTERVAL_SECONDS + 2.0

    def test_dispatch_sleep_seconds_jitter_range(self, league_refresh_utils):
        captured = {}

        def _fake_uniform(low, high):
            captured["low"], captured["high"] = low, high
            return low

        with patch.object(
            league_refresh_utils.random, "uniform", side_effect=_fake_uniform
        ):
            league_refresh_utils.dispatch_sleep_seconds()
        assert captured["low"] == 0
        assert captured["high"] == league_refresh_utils.DISPATCH_JITTER_SECONDS

    def test_pace_dispatch_sleeps(self, league_refresh_utils):
        with (
            patch.object(
                league_refresh_utils, "dispatch_sleep_seconds", return_value=4.2
            ),
            patch.object(league_refresh_utils.time, "sleep") as mock_sleep,
        ):
            league_refresh_utils.pace_dispatch()
        mock_sleep.assert_called_once_with(4.2)


class TestInvokeOnboarderLambda:
    def test_invokes_lambda_successfully_sleeper(self, league_refresh_utils):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 202}
        with patch.object(league_refresh_utils, "_lambda_client", mock_lambda):
            league_refresh_utils.invoke_onboarder_lambda(
                "league-123",
                canonical_league_id="canonical-abc",
                correlation_id="test-corr-id",
                platform="SLEEPER",
            )
        mock_lambda.invoke.assert_called_once()
        payload = json.loads(mock_lambda.invoke.call_args[1]["Payload"])
        assert payload["body"]["leagueId"] == "league-123"
        assert payload["body"]["platform"] == "SLEEPER"
        # Sleeper derives its own seasons; no season is sent.
        assert "season" not in payload["body"]
        assert payload["canonicalLeagueId"] == "canonical-abc"
        assert payload["requestType"] == "REFRESH"
        assert payload["correlation_id"] == "test-corr-id"
        assert payload["ownerUserId"] is None

    def test_invokes_lambda_successfully_yahoo(self, league_refresh_utils):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 202}
        with patch.object(league_refresh_utils, "_lambda_client", mock_lambda):
            league_refresh_utils.invoke_onboarder_lambda(
                "y-2026",
                canonical_league_id="y-canon",
                correlation_id="test-corr-id",
                platform="YAHOO",
                owner_user_id="user-42",
            )
        payload = json.loads(mock_lambda.invoke.call_args[1]["Payload"])
        assert payload["body"]["platform"] == "YAHOO"
        assert "season" not in payload["body"]
        assert payload["ownerUserId"] == "user-42"
        assert payload["requestType"] == "REFRESH"

    def test_invokes_lambda_successfully_espn_with_season(self, league_refresh_utils):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 202}
        with patch.object(league_refresh_utils, "_lambda_client", mock_lambda):
            league_refresh_utils.invoke_onboarder_lambda(
                "e-2026",
                canonical_league_id="e-canon",
                correlation_id="test-corr-id",
                platform="ESPN",
                owner_user_id="user-7",
                season="2026",
            )
        payload = json.loads(mock_lambda.invoke.call_args[1]["Payload"])
        assert payload["body"]["platform"] == "ESPN"
        # ESPN carries the season so the onboarder's ESPN client has a latest season.
        assert payload["body"]["season"] == "2026"
        assert payload["ownerUserId"] == "user-7"

    def test_raises_when_status_not_202(self, league_refresh_utils):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {"StatusCode": 500}
        with (
            patch.object(league_refresh_utils, "_lambda_client", mock_lambda),
            pytest.raises(Exception, match="status code 500"),
        ):
            league_refresh_utils.invoke_onboarder_lambda(
                "league-123",
                canonical_league_id="canonical-abc",
                correlation_id="test-corr-id",
                platform="SLEEPER",
            )
