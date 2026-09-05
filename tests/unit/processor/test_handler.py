"""Tests for processor/handler.py I/O helpers and the lambda handler orchestration.

Pure transformation functions are covered in test_pure_functions.py; this file
covers the S3/DynamoDB-touching helpers and _lambda_handler_impl, which wires
them together.
"""

import datetime as dt
import json
from unittest.mock import MagicMock, patch

import botocore.exceptions
import duckdb
import pytest


class TestReadS3Object:
    def test_reads_and_parses_json(self, processor_handler):
        mock_s3 = MagicMock()
        body = MagicMock()
        body.read.return_value = json.dumps({"key": "val"}).encode("utf-8")
        mock_s3.get_object.return_value = {"Body": body}
        with patch.object(processor_handler, "s3_client", mock_s3):
            result = processor_handler.read_s3_object("bucket", "key")
        assert result == {"key": "val"}
        mock_s3.get_object.assert_called_once_with(Bucket="bucket", Key="key")

    def test_passes_version_id_when_provided(self, processor_handler):
        mock_s3 = MagicMock()
        body = MagicMock()
        body.read.return_value = b"[]"
        mock_s3.get_object.return_value = {"Body": body}
        with patch.object(processor_handler, "s3_client", mock_s3):
            processor_handler.read_s3_object("bucket", "key", version_id="v1")
        assert mock_s3.get_object.call_args[1]["VersionId"] == "v1"

    def test_raises_on_client_error(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "x"}}, "GetObject"
        )
        with (
            patch.object(processor_handler, "s3_client", mock_s3),
            pytest.raises(botocore.exceptions.ClientError),
        ):
            processor_handler.read_s3_object("bucket", "key")


class TestGetPreviousVersionId:
    def test_returns_second_most_recent_version(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.list_object_versions.return_value = {
            "Versions": [
                {
                    "Key": "k",
                    "VersionId": "v1",
                    "LastModified": dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc),
                },
                {
                    "Key": "k",
                    "VersionId": "v2",
                    "LastModified": dt.datetime(2024, 1, 2, tzinfo=dt.timezone.utc),
                },
            ]
        }
        with patch.object(processor_handler, "s3_client", mock_s3):
            result = processor_handler.get_previous_version_id("b", "k")
        assert result == "v1"  # v2 is newest, v1 is the previous version

    def test_returns_none_with_single_version(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.list_object_versions.return_value = {
            "Versions": [
                {
                    "Key": "k",
                    "VersionId": "v1",
                    "LastModified": dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc),
                },
            ]
        }
        with patch.object(processor_handler, "s3_client", mock_s3):
            assert processor_handler.get_previous_version_id("b", "k") is None

    def test_filters_out_other_keys(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.list_object_versions.return_value = {
            "Versions": [
                {
                    "Key": "k",
                    "VersionId": "v1",
                    "LastModified": dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc),
                },
                {
                    "Key": "other",
                    "VersionId": "v9",
                    "LastModified": dt.datetime(2024, 1, 5, tzinfo=dt.timezone.utc),
                },
            ]
        }
        with patch.object(processor_handler, "s3_client", mock_s3):
            # Only one version matches the key, so there is no previous version.
            assert processor_handler.get_previous_version_id("b", "k") is None


class TestBuildESPNBracketsBranches:
    def test_team_2_wins_round_one(self, processor_handler):
        # Covers the `elif winner == team_2` branch.
        matchups = [
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
                "week": 15,
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": 2,
                "loser": 1,
            }
        ]
        result = processor_handler._build_espn_brackets(matchups)
        assert result[0]["winner"] == "2"

    def test_playoff_tie_has_no_winner(self, processor_handler):
        # A tied playoff game leaves winner None, so neither the team_1 nor team_2
        # win branch is taken when recording round results.
        matchups = [
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
                "week": 15,
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": "TIE",
                "loser": "TIE",
            }
        ]
        result = processor_handler._build_espn_brackets(matchups)
        assert result[0]["winner"] is None
        assert result[0]["loser"] is None

    def test_round_two_entry_with_empty_team_skips_from_link(self, processor_handler):
        # A round-2 entry whose team_1 is empty exercises the `if team_id:` false
        # branch in the team_from back-linking loop.
        matchups = [
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
                "week": 15,
                "team_a_id": 2,
                "team_b_id": 3,
                "winner": 2,
                "loser": 3,
            },
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
                "week": 16,
                "team_a_id": "",  # empty team in round 2
                "team_b_id": 2,
                "winner": 2,
                "loser": "",
            },
        ]
        result = processor_handler._build_espn_brackets(matchups)
        round_two = next(e for e in result if e["round"] == 2)
        assert round_two["team_1_from"] is None  # empty team got no back-link


class TestRegisterESPNRawDataMatchups:
    def test_parses_full_matchup_with_rosters(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": {
                    "matchups": [
                        {
                            "matchupPeriodId": 1,
                            "playoffTierType": "NONE",
                            "home": {
                                "teamId": 1,
                                "totalPoints": "100.0",
                                "rosterForMatchupPeriod": {
                                    "entries": [
                                        {
                                            "playerId": 11,
                                            "lineupSlotId": 0,
                                            "playerPoolEntry": {
                                                "player": {
                                                    "fullName": "QB One",
                                                    "defaultPositionId": 1,
                                                },
                                                "appliedStatTotal": 20.0,
                                            },
                                        }
                                    ]
                                },
                                "rosterForCurrentScoringPeriod": {
                                    "entries": [
                                        {
                                            "playerId": 11,
                                            "lineupSlotId": 0,
                                            "playerPoolEntry": {
                                                "player": {
                                                    "fullName": "QB One",
                                                    "defaultPositionId": 1,
                                                },
                                                "appliedStatTotal": 20.0,
                                            },
                                        }
                                    ]
                                },
                            },
                            "away": {
                                "teamId": 2,
                                "totalPoints": "90.0",
                                "rosterForMatchupPeriod": {"entries": []},
                                "rosterForCurrentScoringPeriod": {"entries": []},
                            },
                        }
                    ]
                },
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert len(result["matchups"]) == 1
        matchup = result["matchups"][0]
        assert matchup["winner"] == 1  # home outscored away
        assert matchup["loser"] == 2

    def test_tie_matchup_marks_tie(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": {
                    "matchups": [
                        {
                            "matchupPeriodId": 1,
                            "home": {"teamId": 1, "totalPoints": "100.0"},
                            "away": {"teamId": 2, "totalPoints": "100.0"},
                        }
                    ]
                },
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert result["matchups"][0]["winner"] == "TIE"

    def test_away_team_wins(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": {
                    "matchups": [
                        {
                            "matchupPeriodId": 1,
                            "home": {"teamId": 1, "totalPoints": "80.0"},
                            "away": {"teamId": 2, "totalPoints": "120.0"},
                        }
                    ]
                },
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert result["matchups"][0]["winner"] == 2

    def test_settings_without_name_skipped(self, processor_handler):
        # Covers the `if league_name:` false branch for ESPN settings.
        raw = [
            {
                "season": "2024",
                "data_type": "settings",
                "data": {"settings": {}},
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert result["league_name_by_season"] == {}

    def test_unrecognized_data_type_ignored(self, processor_handler):
        # An item matching none of the branches falls through to the next iteration.
        raw = [{"season": "2024", "data_type": "unknown_type", "data": {}}]
        result = processor_handler._register_espn_raw_data(raw)
        assert result["members"] == []

    def test_settings_extracts_league_settings(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "settings",
                "data": {
                    "settings": {
                        "name": "My League",
                        "scheduleSettings": {
                            "playoffTeamCount": 4,
                            "matchupPeriodCount": 14,
                        },
                    }
                },
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert result["league_settings_by_season"]["2024"] == {
            "season": "2024",
            "num_playoff_teams": 4,
            "num_playoff_teams_assumed": False,
            "playoff_week_start": 15,
            "regular_season_weeks": 14,
        }

    def test_settings_missing_playoff_count_defaults(self, processor_handler):
        # No scheduleSettings at all -> defaults (num_playoff_teams 6, season-based week).
        raw = [
            {
                "season": "2024",
                "data_type": "settings",
                "data": {"settings": {"name": "My League"}},
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert result["league_settings_by_season"]["2024"]["num_playoff_teams"] == 6
        assert result["league_settings_by_season"]["2024"]["playoff_week_start"] == 15


class TestTraceSleeperChampionshipPathContinue:
    def test_skips_unknown_and_revisited_match_ids(self, processor_handler):
        # m3 (final) references match 99 (not in by_id) and match 1 twice, so the
        # stack hits both the "not in by_id" and "already in path" continue cases.
        entries = [
            {"m": 1, "r": 1, "t1": 1, "t2": 2, "p": None},
            {
                "m": 3,
                "r": 2,
                "t1": 1,
                "t2": 2,
                "p": 1,
                "t1_from": {"w": 1},
                "t2_from": {"w": 99},
            },
        ]
        path = processor_handler._trace_sleeper_championship_path(entries)
        assert path == {1, 3}  # 99 ignored, 1 added once


class TestRegisterSleeperRawDataBranches:
    def test_parses_rosters(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "rosters",
                "data": [{"roster_id": 1, "owner_id": "u1"}],
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert len(result["rosters"]) == 1
        assert result["rosters"][0]["season"] == "2024"

    def test_transactions_branch_keeps_only_completed(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "users",
                "data": [
                    {
                        "user_id": "u1",
                        "display_name": "alice",
                        "metadata": {"team_name": "Alice"},
                    }
                ],
            },
            {
                "season": "2024",
                "data_type": "rosters",
                "data": [{"roster_id": 8, "owner_id": "u1"}],
            },
            {
                "season": "2024",
                "data_type": "transactions_week1",
                "data": [
                    {
                        "transaction_id": "ok",
                        "type": "waiver",
                        "status": "complete",
                        "leg": 1,
                        "created": 1,
                        "roster_ids": [8],
                        "adds": {"9504": 8},
                        "drops": None,
                        "draft_picks": [],
                        "settings": {"waiver_bid": 5},
                    },
                    {
                        "transaction_id": "failed",
                        "type": "waiver",
                        "status": "failed",
                        "leg": 1,
                        "created": 2,
                        "roster_ids": [8],
                        "adds": {"9504": 8},
                        "drops": None,
                        "draft_picks": [],
                        "settings": {},
                    },
                ],
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert len(result["transactions"]) == 1
        txn = result["transactions"][0]
        assert txn["transaction_id"] == "ok"
        assert txn["teams"][0]["team_name"] == "Alice"

    def test_league_settings_roster_positions_collected(self, processor_handler):
        # Covers the roster_positions pre-pass assignment and team_b-wins matchup.
        raw = [
            {
                "season": "2024",
                "data_type": "league_settings",
                "data": {
                    "roster_positions": ["QB", "RB", "BN"],
                    "settings": {"playoff_week_start": 15},
                },
            },
            {
                "season": "2024",
                "data_type": "matchupsweek1",
                "data": [
                    {
                        "matchup_id": 1,
                        "roster_id": 1,
                        "points": 80.0,
                        "starters": [],
                        "starters_points": [],
                    },
                    {
                        "matchup_id": 1,
                        "roster_id": 2,
                        "points": 120.0,
                        "starters": [],
                        "starters_points": [],
                    },
                ],
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["matchups"][0]["winner"] == 2  # team_b outscored team_a

    def test_league_settings_extracted(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "league_settings",
                "data": {
                    "name": "My League",
                    "settings": {"playoff_week_start": 15, "playoff_teams": 6},
                },
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["league_settings_by_season"]["2024"] == {
            "season": "2024",
            "num_playoff_teams": 6,
            "num_playoff_teams_assumed": False,
            "playoff_week_start": 15,
            "regular_season_weeks": 14,
        }

    def test_league_settings_missing_playoff_teams_defaults(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "league_settings",
                "data": {"settings": {"playoff_week_start": 15}},
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["league_settings_by_season"]["2024"]["num_playoff_teams"] == 6

    def test_tie_matchup_marks_tie(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "matchupsweek1",
                "data": [
                    {"matchup_id": 1, "roster_id": 1, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 2, "points": 100.0},
                ],
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["matchups"][0]["winner"] == "TIE"

    def test_unpaired_matchup_skipped(self, processor_handler):
        # A matchup_id with only one team is not a valid pairing and is skipped.
        raw = [
            {
                "season": "2024",
                "data_type": "matchupsweek1",
                "data": [{"matchup_id": 1, "roster_id": 1, "points": 100.0}],
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["matchups"] == []

    @pytest.mark.parametrize("bracket_data", [[], None])
    def test_empty_or_null_bracket_yields_no_bracket_rows(
        self, processor_handler, bracket_data
    ):
        # A season with no playoffs yet carries an empty (normalized) or null
        # bracket payload; this must produce zero bracket rows, not a crash.
        raw = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": bracket_data,
            },
            {
                "season": "2024",
                "data_type": "losers_bracket",
                "data": bracket_data,
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["brackets"] == []


class TestRegisterRawDataRegistersViews:
    def test_espn_registers_dataframes(self, processor_handler):
        # The inner parser is covered separately; here we verify register_raw_data
        # routes to it and registers each non-metadata group as a DuckDB view.
        con = duckdb.connect()
        grouped = {
            "members": [{"id": "m1"}],
            "teams": [{"id": 1}],
            "league_name_by_season": {"2024": "X"},
        }
        with patch.object(
            processor_handler, "_register_espn_raw_data", return_value=grouped
        ):
            result = processor_handler.register_raw_data([], con, platform="ESPN")
        assert result is grouped
        registered = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        assert "members" in registered
        assert "teams" in registered
        assert "league_name_by_season" not in registered  # skipped, not a view

    def test_sleeper_registers_dataframes(self, processor_handler):
        con = duckdb.connect()
        grouped = {
            "users": [{"user_id": "u1"}],
            "league_name_by_season": {},
        }
        with patch.object(
            processor_handler, "_register_sleeper_raw_data", return_value=grouped
        ):
            result = processor_handler.register_raw_data(
                [], con, platform="SLEEPER", player_metadata={}, player_stats={}
            )
        assert result is grouped
        registered = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        assert "users" in registered

    def test_empty_brackets_registered_as_typed_view(self, processor_handler):
        # A season with no playoffs yields an empty brackets list; it must still be
        # registered as a typed (numeric) view so downstream queries bind and return
        # no rows rather than crashing on a 0-column frame.
        con = duckdb.connect()
        grouped = {
            "brackets": [],
            "league_name_by_season": {},
        }
        with patch.object(
            processor_handler, "_register_sleeper_raw_data", return_value=grouped
        ):
            processor_handler.register_raw_data(
                [], con, platform="SLEEPER", player_metadata={}, player_stats={}
            )
        registered = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        assert "brackets" in registered
        # Seeding arithmetic requires position to bind as numeric, not VARCHAR.
        assert (
            con.execute("SELECT SUM(position + 1) FROM brackets").fetchone()[0] is None
        )

    def test_empty_transactions_registered_as_typed_view(self, processor_handler):
        # A Sleeper league whose onboarded seasons carry no completed transactions yields
        # an empty transactions list; it must still register as a typed view so the
        # TRANSACTIONS passthrough binds and returns no rows rather than crashing on a
        # 0-column frame ("Need a DataFrame with at least one column").
        con = duckdb.connect()
        grouped = {
            "transactions": [],
            "league_name_by_season": {},
        }
        with patch.object(
            processor_handler, "_register_sleeper_raw_data", return_value=grouped
        ):
            processor_handler.register_raw_data(
                [], con, platform="SLEEPER", player_metadata={}, player_stats={}
            )
        registered = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        assert "transactions" in registered
        # The TRANSACTIONS transform orders by season/created; both columns must exist and
        # the empty view must yield no rows.
        rows = con.execute(
            "SELECT * FROM transactions ORDER BY season DESC, created DESC"
        ).fetchall()
        assert rows == []

    def test_empty_player_scoring_totals_registered_as_typed_view(
        self, processor_handler
    ):
        # A Sleeper league onboarded before its first games (e.g. a new season created in
        # the preseason) has no accumulated player stats yet, so player_scoring_totals is
        # empty. It must still register as a typed view — with total_points numeric — so
        # the DRAFT (SLEEPER) transform binds and returns no rows rather than crashing on a
        # 0-column frame ("Need a DataFrame with at least one column").
        con = duckdb.connect()
        grouped = {
            "player_scoring_totals": [],
            "league_name_by_season": {},
        }
        with patch.object(
            processor_handler, "_register_sleeper_raw_data", return_value=grouped
        ):
            processor_handler.register_raw_data(
                [], con, platform="SLEEPER", player_metadata={}, player_stats={}
            )
        registered = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        assert "player_scoring_totals" in registered
        # VORP/rank arithmetic requires total_points to bind as numeric, not VARCHAR.
        assert (
            con.execute(
                "SELECT SUM(total_points + 1) FROM player_scoring_totals"
            ).fetchone()[0]
            is None
        )
        assert con.execute("SELECT * FROM player_scoring_totals").fetchall() == []

    def test_unguarded_empty_view_logs_and_raises(self, processor_handler):
        # A view that is empty but NOT in _EMPTY_VIEW_DTYPES becomes a 0-column frame that
        # DuckDB rejects. The offending view must be logged by name before the failure so
        # it is attributable from the logs, and the error must still propagate.
        con = duckdb.connect()
        grouped = {
            "rosters": [],
            "league_name_by_season": {},
        }
        with (
            patch.object(
                processor_handler, "_register_sleeper_raw_data", return_value=grouped
            ),
            patch.object(processor_handler, "logger") as mock_logger,
            pytest.raises(duckdb.InvalidInputException),
        ):
            processor_handler.register_raw_data(
                [], con, platform="SLEEPER", player_metadata={}, player_stats={}
            )
        logged_views = [call.args[1] for call in mock_logger.error.call_args_list]
        assert "rosters" in logged_views


class TestWriteItems:
    def test_batch_writes_each_item(self, processor_handler):
        mock_table = MagicMock()
        writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = writer
        items = [
            {"PK": "p", "SK": "s1", "data": []},
            {"PK": "p", "SK": "s2", "data": []},
        ]
        with patch.object(processor_handler, "table", mock_table):
            processor_handler.write_items(items)
        assert writer.put_item.call_count == 2
        writer.put_item.assert_any_call(Item=items[0])


class TestDeleteItems:
    def test_batch_deletes_each_key(self, processor_handler):
        mock_table = MagicMock()
        writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__.return_value = writer
        with patch.object(processor_handler, "table", mock_table):
            processor_handler.delete_items("LEAGUE#abc", ["TRANSACTIONS#2024"])
        writer.delete_item.assert_called_once_with(
            Key={"PK": "LEAGUE#abc", "SK": "TRANSACTIONS#2024"}
        )

    def test_empty_sks_is_a_noop(self, processor_handler):
        mock_table = MagicMock()
        with patch.object(processor_handler, "table", mock_table):
            processor_handler.delete_items("LEAGUE#abc", [])
        mock_table.batch_writer.assert_not_called()


def _s3_event(key="raw/canonical-abc/manifest.json", principal="AWS:role/abc"):
    return {
        "Records": [
            {
                "userIdentity": {"principalId": principal},
                "s3": {"bucket": {"name": "bucket"}, "object": {"key": key}},
            }
        ]
    }


def _manifest_response(manifest: dict, correlation_id="corr-1"):
    body = MagicMock()
    body.read.return_value = json.dumps(manifest).encode("utf-8")
    return {"Body": body, "Metadata": {"correlation_id": correlation_id}}


_FAKE_QUERIES = {
    "TEAMS": {"ESPN": "SELECT 1", "SLEEPER": "SELECT 1"},
    "MATCHUPS": {"ESPN": "SELECT 1", "SLEEPER": "SELECT 1"},
    "PLAYOFF_BRACKET": {"ESPN": "SELECT 1", "SLEEPER": "SELECT 1"},
    "DRAFT": {"ESPN": "SELECT 1", "SLEEPER": "SELECT 1"},
    "STANDINGS": "SELECT 1",
    "WEEKLY_STANDINGS": "SELECT 1",
}


class TestProcessorTracePropagation:
    """The processor continues the onboarder's trace from the manifest metadata (backend/otel-tracing)."""

    def test_continues_trace_from_manifest_metadata(self, processor_handler):
        mock_s3 = MagicMock()
        resp = _manifest_response({"SLEEPER": ["2024"]})
        resp["Metadata"]["traceparent"] = "00-abc-def-01"
        mock_s3.get_object.return_value = resp
        proc = MagicMock()
        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                _process_manifest=proc,
            ),
            patch.object(processor_handler, "traced_handler") as th,
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())
        th.assert_called_once_with(
            "processor.handle",
            carrier={"correlation_id": "corr-1", "traceparent": "00-abc-def-01"},
        )
        proc.assert_called_once()


class TestLambdaHandlerImpl:
    def test_replication_event_returns_early(self, processor_handler):
        mock_s3 = MagicMock()
        with patch.object(processor_handler, "s3_client", mock_s3):
            processor_handler._lambda_handler_impl(
                _s3_event(principal="AWS:s3-replication"), MagicMock()
            )
        mock_s3.get_object.assert_not_called()

    def test_malformed_event_raises_value_error(self, processor_handler):
        with pytest.raises(ValueError, match="Unexpected S3 event structure"):
            processor_handler._lambda_handler_impl({"Records": []}, MagicMock())

    def test_espn_onboard_processes_and_increments_count(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"ESPN": ["2024"]})
        grouped = {"league_name_by_season": {"2024": "My League"}}
        write_meta = MagicMock()
        update_count = MagicMock()
        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(
                    return_value=[{"data_type": "users", "data": {}}]
                ),
                register_raw_data=MagicMock(return_value=grouped),
                dataframe_to_dynamo_items=MagicMock(return_value=[]),
                write_items=MagicMock(),
                write_metadata_items=write_meta,
                update_league_count=update_count,
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())
        update_count.assert_called_once_with(delta=1)
        # league_name extracted from the most recent season and passed through.
        assert write_meta.call_args[1]["league_name"] == "My League"
        assert write_meta.call_args[1]["refresh"] is False

    def test_league_settings_view_written(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"SLEEPER": ["2024"]})
        grouped = {
            "league_name_by_season": {"2024": "My League"},
            "league_settings_by_season": {
                "2024": {
                    "season": "2024",
                    "num_playoff_teams": 6,
                    "playoff_week_start": 15,
                    "regular_season_weeks": 14,
                }
            },
        }
        write_items = MagicMock()

        def fake_read(bucket, key, version_id=None):
            if key.endswith(("players.json", "player_stats.json")):
                return {}
            return [{"data_type": "users", "data": []}]

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(side_effect=fake_read),
                register_raw_data=MagicMock(return_value=grouped),
                dataframe_to_dynamo_items=MagicMock(return_value=[]),
                write_items=write_items,
                write_metadata_items=MagicMock(),
                update_league_count=MagicMock(),
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

        # One write_items call carries the LEAGUE_SETTINGS item with the season's data.
        settings_items = [
            item
            for call in write_items.call_args_list
            for item in call.kwargs["items"]
            if item["SK"] == "LEAGUE_SETTINGS#2024"
        ]
        assert len(settings_items) == 1
        assert settings_items[0]["data"][0]["num_playoff_teams"] == 6
        assert settings_items[0]["data"][0]["regular_season_weeks"] == 14

    def test_sleeper_refresh_reads_previous_manifest_and_player_data(
        self, processor_handler
    ):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"SLEEPER": ["2024"]})
        write_meta = MagicMock()
        update_count = MagicMock()

        def fake_read(bucket, key, version_id=None):
            if version_id:
                return {"SLEEPER": ["2024"]}  # previous manifest
            if key.endswith("sleeper_nfl_players.json"):
                return {"p1": {"full_name": "Player One"}}
            if key.endswith("sleeper_nfl_player_stats.json"):
                return {"p1": {"2024": {"pts": 10}}}
            return [{"data_type": "users", "data": []}]  # season data

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value="v-prev"),
                read_s3_object=MagicMock(side_effect=fake_read),
                # grouped without a league_name_by_season key exercises the
                # `if "league_name_by_season" in grouped` false branch.
                register_raw_data=MagicMock(return_value={}),
                dataframe_to_dynamo_items=MagicMock(return_value=[]),
                write_items=MagicMock(),
                write_metadata_items=write_meta,
                update_league_count=update_count,
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())
        # Refresh: count is not incremented and refresh flag is set.
        update_count.assert_not_called()
        assert write_meta.call_args[1]["refresh"] is True

    def test_reprocess_all_processes_every_season_and_skips_previous_manifest(
        self, processor_handler
    ):
        mock_s3 = MagicMock()
        manifest = _manifest_response({"SLEEPER": ["2023", "2024"]})
        manifest["Metadata"]["reprocess_all"] = "true"
        mock_s3.get_object.return_value = manifest
        read_keys: list = []

        def fake_read(bucket, key, version_id=None):
            read_keys.append((key, version_id))
            if key.endswith(("players.json", "player_stats.json")):
                return {}
            return [{"data_type": "users", "data": []}]

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value="v-prev"),
                read_s3_object=MagicMock(side_effect=fake_read),
                register_raw_data=MagicMock(return_value={}),
                dataframe_to_dynamo_items=MagicMock(return_value=[]),
                write_items=MagicMock(),
                write_metadata_items=MagicMock(),
                update_league_count=MagicMock(),
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

        # No versioned (previous-manifest) read happened, and both seasons were read.
        assert all(version_id is None for _, version_id in read_keys)
        season_files = {key for key, _ in read_keys if key.endswith(".json")}
        assert any(k.endswith("/2023.json") for k in season_files)
        assert any(k.endswith("/2024.json") for k in season_files)

    def test_sleeper_transactions_schema_written_when_present(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"SLEEPER": ["2024"]})
        df_to_items = MagicMock(return_value=[])
        fake_queries = {
            **_FAKE_QUERIES,
            "TRANSACTIONS": {"SLEEPER": "SELECT 1"},
        }

        def fake_read(bucket, key, version_id=None):
            if key.endswith(("players.json", "player_stats.json")):
                return {}
            return [{"data_type": "users", "data": []}]

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(side_effect=fake_read),
                register_raw_data=MagicMock(
                    return_value={"transactions": [{"season": "2024"}]}
                ),
                dataframe_to_dynamo_items=df_to_items,
                write_items=MagicMock(),
                write_metadata_items=MagicMock(),
                update_league_count=MagicMock(),
                QUERIES=fake_queries,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

        entity_types = {
            call.kwargs["schema"].entity_type for call in df_to_items.call_args_list
        }
        assert processor_handler.EntityType.TRANSACTIONS in entity_types

    def test_transactions_bare_keys_deleted_before_chunk_writes(
        self, processor_handler
    ):
        # On an initial onboard every season is processed, so the legacy bare
        # TRANSACTIONS#{season} item is deleted for each season before its chunks are
        # written (delete-before-write), preventing a stale bare item from coexisting
        # with chunks.
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response(
            {"SLEEPER": ["2023", "2024"]}
        )
        fake_queries = {**_FAKE_QUERIES, "TRANSACTIONS": {"SLEEPER": "SELECT 1"}}

        def fake_read(bucket, key, version_id=None):
            if key.endswith(("players.json", "player_stats.json")):
                return {}
            return [{"data_type": "users", "data": []}]

        manager = MagicMock()
        delete_mock = MagicMock()
        write_mock = MagicMock()
        manager.attach_mock(delete_mock, "delete_items")
        manager.attach_mock(write_mock, "write_items")

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(side_effect=fake_read),
                register_raw_data=MagicMock(
                    return_value={"transactions": [{"season": "2023"}]}
                ),
                dataframe_to_dynamo_items=MagicMock(return_value=[]),
                delete_items=delete_mock,
                write_items=write_mock,
                write_metadata_items=MagicMock(),
                update_league_count=MagicMock(),
                QUERIES=fake_queries,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

        # Exactly one delete call, targeting the bare key for every processed season.
        delete_mock.assert_called_once_with(
            pk="LEAGUE#canonical-abc",
            sks=["TRANSACTIONS#2023", "TRANSACTIONS#2024"],
        )
        # The delete is immediately followed by a write (the transactions chunk write).
        call_names = [c[0] for c in manager.mock_calls]
        delete_index = call_names.index("delete_items")
        assert call_names[delete_index + 1] == "write_items"

    def test_transactions_delete_targets_only_processed_seasons_on_refresh(
        self, processor_handler
    ):
        # An in-season refresh processes only the last season, so only that season's
        # bare key is deleted; other seasons' items are left untouched.
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response(
            {"SLEEPER": ["2023", "2024"]}
        )
        fake_queries = {**_FAKE_QUERIES, "TRANSACTIONS": {"SLEEPER": "SELECT 1"}}

        def fake_read(bucket, key, version_id=None):
            if version_id:
                return {"SLEEPER": ["2023", "2024"]}  # previous manifest, same seasons
            if key.endswith(("players.json", "player_stats.json")):
                return {}
            return [{"data_type": "users", "data": []}]

        delete_mock = MagicMock()

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value="v-prev"),
                read_s3_object=MagicMock(side_effect=fake_read),
                register_raw_data=MagicMock(
                    return_value={"transactions": [{"season": "2024"}]}
                ),
                dataframe_to_dynamo_items=MagicMock(return_value=[]),
                delete_items=delete_mock,
                write_items=MagicMock(),
                write_metadata_items=MagicMock(),
                update_league_count=MagicMock(),
                QUERIES=fake_queries,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

        delete_mock.assert_called_once_with(
            pk="LEAGUE#canonical-abc",
            sks=["TRANSACTIONS#2024"],
        )

    def test_espn_never_writes_transactions_schema(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"ESPN": ["2024"]})
        df_to_items = MagicMock(return_value=[])
        # Even if a (hypothetical) transactions group were present, ESPN must not
        # produce a TRANSACTIONS view — the schema is Sleeper-gated.
        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(
                    return_value=[{"data_type": "users", "data": {}}]
                ),
                register_raw_data=MagicMock(
                    return_value={"transactions": [{"season": "2024"}]}
                ),
                dataframe_to_dynamo_items=df_to_items,
                write_items=MagicMock(),
                write_metadata_items=MagicMock(),
                update_league_count=MagicMock(),
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())
        entity_types = {
            call.kwargs["schema"].entity_type for call in df_to_items.call_args_list
        }
        assert processor_handler.EntityType.TRANSACTIONS not in entity_types

    def test_sleeper_missing_player_metadata_and_stats_warns(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"SLEEPER": ["2024"]})
        not_found = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "x"}}, "GetObject"
        )

        def fake_read(bucket, key, version_id=None):
            if key.endswith("sleeper_nfl_players.json"):
                raise not_found
            if key.endswith("sleeper_nfl_player_stats.json"):
                raise not_found
            return [{"data_type": "users", "data": []}]

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(side_effect=fake_read),
                register_raw_data=MagicMock(return_value={"league_name_by_season": {}}),
                dataframe_to_dynamo_items=MagicMock(return_value=[]),
                write_items=MagicMock(),
                write_metadata_items=MagicMock(),
                update_league_count=MagicMock(),
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            # Missing metadata/stats are tolerated (warnings, not failures).
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

    def test_sleeper_player_metadata_other_error_raises(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"SLEEPER": ["2024"]})
        other_error = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "x"}}, "GetObject"
        )

        def fake_read(bucket, key, version_id=None):
            if key.endswith("sleeper_nfl_players.json"):
                raise other_error
            return [{"data_type": "users", "data": []}]

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(side_effect=fake_read),
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
            pytest.raises(botocore.exceptions.ClientError),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

    def test_sleeper_player_stats_other_error_raises(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"SLEEPER": ["2024"]})
        other_error = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "x"}}, "GetObject"
        )

        def fake_read(bucket, key, version_id=None):
            if key.endswith("sleeper_nfl_players.json"):
                return {"p1": {}}
            if key.endswith("sleeper_nfl_player_stats.json"):
                raise other_error
            return [{"data_type": "users", "data": []}]

        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(side_effect=fake_read),
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
            pytest.raises(botocore.exceptions.ClientError),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

    def test_failed_season_read_raises_runtime_error(self, processor_handler):
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"ESPN": ["2024"]})
        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(side_effect=RuntimeError("S3 down")),
                QUERIES=_FAKE_QUERIES,
            ),
            pytest.raises(RuntimeError, match="Failed to load seasons"),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())

    def test_no_league_name_when_grouping_empty(self, processor_handler):
        # grouped has an empty league_name_by_season -> league_name stays None.
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = _manifest_response({"ESPN": ["2024"]})
        write_meta = MagicMock()
        with (
            patch.multiple(
                processor_handler,
                s3_client=mock_s3,
                get_previous_version_id=MagicMock(return_value=None),
                read_s3_object=MagicMock(
                    return_value=[{"data_type": "users", "data": {}}]
                ),
                register_raw_data=MagicMock(return_value={"league_name_by_season": {}}),
                dataframe_to_dynamo_items=MagicMock(return_value=[]),
                write_items=MagicMock(),
                write_metadata_items=write_meta,
                update_league_count=MagicMock(),
                QUERIES=_FAKE_QUERIES,
            ),
            patch.object(processor_handler.duckdb, "connect", return_value=MagicMock()),
        ):
            processor_handler._lambda_handler_impl(_s3_event(), MagicMock())
        assert write_meta.call_args[1]["league_name"] is None
