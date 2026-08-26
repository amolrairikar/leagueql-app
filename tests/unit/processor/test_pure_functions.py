"""Tests for pure functions in processor/handler.py."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest


class TestSanitizeValue:
    def test_float_becomes_decimal(self, processor_handler):
        result = processor_handler.sanitize_value(1.5)
        assert result == Decimal("1.5")
        assert isinstance(result, Decimal)

    def test_list_of_floats_sanitized(self, processor_handler):
        result = processor_handler.sanitize_value([1.5, 2.5])
        assert result == [Decimal("1.5"), Decimal("2.5")]

    def test_nested_dict_sanitized(self, processor_handler):
        result = processor_handler.sanitize_value({"a": 1.5, "b": {"c": 2.5}})
        assert result["a"] == Decimal("1.5")
        assert result["b"]["c"] == Decimal("2.5")

    def test_non_float_unchanged(self, processor_handler):
        assert processor_handler.sanitize_value("hello") == "hello"
        assert processor_handler.sanitize_value(42) == 42
        assert processor_handler.sanitize_value(None) is None


class TestResolveSeasons:
    def test_no_previous_seasons_returns_all(self, processor_handler):
        result = processor_handler.resolve_seasons_to_process(
            ["2022", "2023", "2024"], None
        )
        assert result == ["2022", "2023", "2024"]

    def test_new_seasons_detected_returns_only_new(self, processor_handler):
        result = processor_handler.resolve_seasons_to_process(
            ["2022", "2023", "2024"], ["2022", "2023"]
        )
        assert result == ["2024"]

    def test_same_seasons_returns_last(self, processor_handler):
        result = processor_handler.resolve_seasons_to_process(
            ["2022", "2023"], ["2022", "2023"]
        )
        assert result == ["2023"]

    def test_multiple_new_seasons_returned(self, processor_handler):
        result = processor_handler.resolve_seasons_to_process(
            ["2022", "2023", "2024", "2025"], ["2022"]
        )
        assert result == ["2023", "2024", "2025"]


class TestCompileESPNBenchStats:
    def _make_roster(self, players):
        return {
            "entries": [
                {
                    "playerId": p["id"],
                    "playerPoolEntry": {
                        "player": {
                            "fullName": p["name"],
                            "defaultPositionId": p.get("pos_id", 1),
                        },
                        "appliedStatTotal": p.get("points", 0.0),
                    },
                }
                for p in players
            ]
        }

    def test_excludes_starters(self, processor_handler):
        roster = self._make_roster(
            [
                {"id": 1, "name": "Starter", "points": 20.0},
                {"id": 2, "name": "Bench Guy", "points": 5.0},
            ]
        )
        result = processor_handler.compile_espn_bench_stats(roster, starter_ids=[1])
        assert len(result) == 1
        assert result[0]["player_id"] == 2

    def test_empty_roster_returns_empty(self, processor_handler):
        result = processor_handler.compile_espn_bench_stats({}, starter_ids=[])
        assert result == []

    def test_position_mapped_correctly(self, processor_handler):
        roster = self._make_roster(
            [{"id": 5, "name": "K Guy", "pos_id": 5, "points": 10.0}]
        )
        result = processor_handler.compile_espn_bench_stats(roster, starter_ids=[])
        assert result[0]["position"] == "K"


class TestCompileESPNStarterStats:
    def _make_roster(self, players):
        return {
            "entries": [
                {
                    "playerId": p["id"],
                    "lineupSlotId": p.get("slot_id", 0),
                    "playerPoolEntry": {
                        "player": {
                            "fullName": p["name"],
                            "defaultPositionId": p.get("pos_id", 1),
                            "eligibleSlots": p.get("eligible_slots", [0]),
                        },
                        "appliedStatTotal": p.get("points", 0.0),
                    },
                }
                for p in players
            ]
        }

    def test_returns_stats_and_ids(self, processor_handler):
        roster = self._make_roster(
            [
                {"id": 1, "name": "QB Guy", "pos_id": 1, "slot_id": 0},
            ]
        )
        slot_map = {1: 0}
        stats, ids = processor_handler.compile_espn_starter_stats(roster, slot_map)
        assert len(stats) == 1
        assert ids == [1]

    def test_uses_slot_map_for_fantasy_position(self, processor_handler):
        roster = self._make_roster(
            [
                {"id": 1, "name": "RB Guy", "pos_id": 2, "slot_id": 0},
            ]
        )
        slot_map = {1: 2}  # slot 2 = RB
        stats, _ids = processor_handler.compile_espn_starter_stats(roster, slot_map)
        assert stats[0]["fantasy_position"] == "RB"

    def test_falls_back_to_eligible_slots_when_not_in_slot_map(self, processor_handler):
        roster = self._make_roster(
            [
                {
                    "id": 99,
                    "name": "WR Guy",
                    "pos_id": 3,
                    "slot_id": 4,
                    "eligible_slots": [4],
                },
            ]
        )
        stats, _ids = processor_handler.compile_espn_starter_stats(roster, slot_map={})
        assert stats[0]["fantasy_position"] == "WR"

    @pytest.mark.parametrize(
        "slot_id,expected",
        [
            (0, "QB"),
            (1, "TQB"),
            (2, "RB"),
            (3, "RB/WR"),
            (4, "WR"),
            (5, "WR/TE"),
            (6, "TE"),
            (7, "OP"),
            (8, "DT"),
            (9, "DE"),
            (10, "LB"),
            (11, "DL"),
            (12, "CB"),
            (13, "S"),
            (14, "DB"),
            (15, "DP"),
            (16, "D/ST"),
            (17, "K"),
            (18, "P"),
            (19, "HC"),
            (23, "FLEX"),
            (24, "EDR"),
        ],
    )
    def test_all_lineup_slots_mapped(self, processor_handler, slot_id, expected):
        roster = self._make_roster([{"id": 1, "name": "Player", "slot_id": slot_id}])
        slot_map = {1: slot_id}
        stats, _ = processor_handler.compile_espn_starter_stats(roster, slot_map)
        assert stats[0]["fantasy_position"] == expected

    def test_superflex_op_slot_not_collapsed_to_flex(self, processor_handler):
        # Slot 7 (OP / Superflex) must resolve to "OP", not the "FLEX" fallback.
        roster = self._make_roster([{"id": 1, "name": "QB in superflex", "pos_id": 1}])
        slot_map = {1: 7}
        stats, _ = processor_handler.compile_espn_starter_stats(roster, slot_map)
        assert stats[0]["fantasy_position"] == "OP"

    def test_unknown_slot_falls_back_to_flex(self, processor_handler):
        # A slot ID outside the mapping (e.g. bench=20) defaults to "FLEX".
        roster = self._make_roster([{"id": 1, "name": "Unknown slot"}])
        slot_map = {1: 20}
        stats, _ = processor_handler.compile_espn_starter_stats(roster, slot_map)
        assert stats[0]["fantasy_position"] == "FLEX"

    def test_empty_roster(self, processor_handler):
        stats, ids = processor_handler.compile_espn_starter_stats({}, {})
        assert stats == []
        assert ids == []


class TestSleeperPlayerDisplayFields:
    def test_joins_name_and_keeps_position(self, processor_handler):
        full_name, position = processor_handler.sleeper_player_display_fields(
            {"first_name": "Joe", "last_name": "Burrow", "position": "QB"}
        )
        assert full_name == "Joe Burrow"
        assert position == "QB"

    def test_normalizes_def_to_dst(self, processor_handler):
        _, position = processor_handler.sleeper_player_display_fields(
            {"first_name": "Cowboys", "last_name": "", "position": "DEF"}
        )
        assert position == "D/ST"

    def test_missing_metadata_yields_empty_name_and_none_position(
        self, processor_handler
    ):
        full_name, position = processor_handler.sleeper_player_display_fields({})
        assert full_name == ""
        assert position is None


class TestCompileSleeperStarterStats:
    def test_builds_stats_from_starters_and_points(self, processor_handler):
        metadata = {
            "1": {"first_name": "Joe", "last_name": "Burrow", "position": "QB"},
        }
        stats, ids = processor_handler.compile_sleeper_starter_stats(
            starters=["1"],
            starters_points=[25.5],
            player_metadata=metadata,
        )
        assert len(stats) == 1
        assert stats[0]["full_name"] == "Joe Burrow"
        assert stats[0]["points_scored"] == 25.5
        assert stats[0]["position"] == "QB"
        assert ids == ["1"]

    def test_def_position_mapped_to_dst(self, processor_handler):
        metadata = {"99": {"first_name": "Cowboys", "last_name": "", "position": "DEF"}}
        stats, _ = processor_handler.compile_sleeper_starter_stats(
            starters=["99"], starters_points=[10.0], player_metadata=metadata
        )
        assert stats[0]["position"] == "D/ST"

    def test_missing_metadata_uses_empty_strings(self, processor_handler):
        stats, _ = processor_handler.compile_sleeper_starter_stats(
            starters=["999"], starters_points=[5.0], player_metadata={}
        )
        assert stats[0]["full_name"] == ""
        assert stats[0]["position"] is None

    def test_roster_positions_assigns_slot_as_fantasy_position(self, processor_handler):
        metadata = {
            "1": {"first_name": "Joe", "last_name": "Burrow", "position": "QB"},
            "2": {"first_name": "Stefon", "last_name": "Diggs", "position": "WR"},
            "3": {
                "first_name": "Christian",
                "last_name": "McCaffrey",
                "position": "RB",
            },
        }
        roster_positions = ["QB", "WR", "FLEX", "BN", "BN"]
        stats, _ = processor_handler.compile_sleeper_starter_stats(
            starters=["1", "2", "3"],
            starters_points=[28.0, 22.5, 35.1],
            player_metadata=metadata,
            roster_positions=roster_positions,
        )
        assert stats[0]["fantasy_position"] == "QB"
        assert stats[1]["fantasy_position"] == "WR"
        # RB playing in the FLEX slot should be labelled FLEX
        assert stats[2]["fantasy_position"] == "FLEX"

    def test_def_slot_normalised_to_dst(self, processor_handler):
        metadata = {"99": {"first_name": "Cowboys", "last_name": "", "position": "DEF"}}
        stats, _ = processor_handler.compile_sleeper_starter_stats(
            starters=["99"],
            starters_points=[10.0],
            player_metadata=metadata,
            roster_positions=["DEF", "BN"],
        )
        # DEF slot label normalised to D/ST so starters and bench display consistently
        assert stats[0]["fantasy_position"] == "D/ST"

    def test_no_roster_positions_leaves_fantasy_position_none(self, processor_handler):
        metadata = {"1": {"first_name": "Joe", "last_name": "Burrow", "position": "QB"}}
        stats, _ = processor_handler.compile_sleeper_starter_stats(
            starters=["1"], starters_points=[25.5], player_metadata=metadata
        )
        assert stats[0]["fantasy_position"] is None

    def test_bench_slots_excluded_from_starter_slots(self, processor_handler):
        metadata = {
            "1": {"first_name": "A", "last_name": "B", "position": "QB"},
            "2": {"first_name": "C", "last_name": "D", "position": "WR"},
        }
        # BN, IL, IR, TAXI should all be filtered out
        roster_positions = ["QB", "BN", "IL", "IR", "TAXI", "WR", "BN"]
        stats, _ = processor_handler.compile_sleeper_starter_stats(
            starters=["1", "2"],
            starters_points=[20.0, 18.0],
            player_metadata=metadata,
            roster_positions=roster_positions,
        )
        assert stats[0]["fantasy_position"] == "QB"
        assert stats[1]["fantasy_position"] == "WR"


class TestCompileSleeperBenchStats:
    def test_excludes_starters_from_bench(self, processor_handler):
        metadata = {
            "1": {"first_name": "Joe", "last_name": "Burrow", "position": "QB"},
            "2": {"first_name": "Bench", "last_name": "Player", "position": "RB"},
        }
        result = processor_handler.compile_sleeper_bench_stats(
            players=["1", "2"],
            players_points={"1": 25.5, "2": 10.0},
            starter_ids=["1"],
            player_metadata=metadata,
        )
        assert len(result) == 1
        assert result[0]["player_id"] == "2"

    def test_missing_points_defaults_to_zero(self, processor_handler):
        metadata = {"5": {"first_name": "A", "last_name": "B", "position": "WR"}}
        result = processor_handler.compile_sleeper_bench_stats(
            players=["5"],
            players_points={},
            starter_ids=[],
            player_metadata=metadata,
        )
        assert result[0]["points_scored"] == 0.0

    def test_def_position_mapped_to_dst(self, processor_handler):
        metadata = {"88": {"first_name": "Bills", "last_name": "", "position": "DEF"}}
        result = processor_handler.compile_sleeper_bench_stats(
            players=["88"],
            players_points={"88": 8.0},
            starter_ids=[],
            player_metadata=metadata,
        )
        assert result[0]["position"] == "D/ST"


class TestCompileSleeperPlayerScoringTotals:
    def test_calculates_total_points(self, processor_handler):
        player_stats = {"p1": {"2024": {"pass_yd": 300, "pass_td": 2}}}
        scoring_settings = {"2024": {"pass_yd": 0.04, "pass_td": 4.0}}
        metadata = {
            "p1": {"first_name": "Joe", "last_name": "Burrow", "position": "QB"}
        }

        rows = processor_handler.compile_sleeper_player_scoring_totals(
            player_stats=player_stats,
            scoring_settings_by_season=scoring_settings,
            player_metadata=metadata,
        )
        assert len(rows) == 1
        assert rows[0]["player_id"] == "p1"
        assert rows[0]["total_points"] == round(300 * 0.04 + 2 * 4.0, 2)

    def test_skips_player_with_no_stats_for_season(self, processor_handler):
        player_stats = {"p1": {"2023": {"pass_yd": 100}}}
        scoring_settings = {"2024": {"pass_yd": 0.04}}
        metadata = {"p1": {"first_name": "Joe", "last_name": "B", "position": "QB"}}

        rows = processor_handler.compile_sleeper_player_scoring_totals(
            player_stats=player_stats,
            scoring_settings_by_season=scoring_settings,
            player_metadata=metadata,
        )
        assert rows == []

    def test_def_position_mapped_to_dst(self, processor_handler):
        player_stats = {"def1": {"2024": {"sack": 3}}}
        scoring_settings = {"2024": {"sack": 1.0}}
        metadata = {
            "def1": {"first_name": "Cowboys", "last_name": "", "position": "DEF"}
        }

        rows = processor_handler.compile_sleeper_player_scoring_totals(
            player_stats=player_stats,
            scoring_settings_by_season=scoring_settings,
            player_metadata=metadata,
        )
        assert rows[0]["position"] == "D/ST"


class TestBuildSleeperRosterTeamMap:
    def test_maps_roster_to_owner_team_and_display(self, processor_handler):
        users = [
            {
                "user_id": "u1",
                "display_name": "alice",
                "metadata": {"team_name": "Alice's Team"},
                "season": "2024",
            }
        ]
        rosters = [{"roster_id": 1, "owner_id": "u1", "season": "2024"}]
        result = processor_handler.build_sleeper_roster_team_map(users, rosters)
        assert result["2024"]["1"] == {
            "team_name": "Alice's Team",
            "display_name": "alice",
        }

    def test_missing_owner_yields_none_fields(self, processor_handler):
        rosters = [{"roster_id": 2, "owner_id": "ghost", "season": "2024"}]
        result = processor_handler.build_sleeper_roster_team_map([], rosters)
        assert result["2024"]["2"] == {"team_name": None, "display_name": None}

    def test_user_without_metadata_team_name(self, processor_handler):
        users = [
            {
                "user_id": "u1",
                "display_name": "bob",
                "metadata": None,
                "season": "2024",
            }
        ]
        rosters = [{"roster_id": 1, "owner_id": "u1", "season": "2024"}]
        result = processor_handler.build_sleeper_roster_team_map(users, rosters)
        assert result["2024"]["1"]["team_name"] is None
        assert result["2024"]["1"]["display_name"] == "bob"


class TestResolveSleeperTransactionPlayers:
    def test_resolves_name_and_position(self, processor_handler):
        metadata = {
            "9504": {"first_name": "Joe", "last_name": "Mixon", "position": "RB"}
        }
        result = processor_handler._resolve_sleeper_transaction_players(
            {"9504": 8}, metadata
        )
        assert result == [
            {
                "player_id": "9504",
                "player_name": "Joe Mixon",
                "position": "RB",
                "roster_id": "8",
            }
        ]

    def test_none_map_returns_empty(self, processor_handler):
        assert processor_handler._resolve_sleeper_transaction_players(None, {}) == []

    def test_unknown_player_has_null_name(self, processor_handler):
        result = processor_handler._resolve_sleeper_transaction_players(
            {"99999": 3}, {}
        )
        assert result[0]["player_name"] is None
        assert result[0]["position"] is None
        assert result[0]["roster_id"] == "3"


class TestCompileSleeperTransactions:
    def _meta(self):
        return {
            "1": {"first_name": "Joe", "last_name": "Burrow", "position": "QB"},
            "2": {"first_name": "Ja'Marr", "last_name": "Chase", "position": "WR"},
        }

    def _roster_map(self):
        return {
            "2024": {
                "8": {"team_name": "Team Eight", "display_name": "user8"},
                "9": {"team_name": "Team Nine", "display_name": "user9"},
            }
        }

    def test_waiver_resolves_players_and_team(self, processor_handler):
        txn = {
            "transaction_id": "t1",
            "type": "waiver",
            "status": "complete",
            "leg": 1,
            "created": 100,
            "roster_ids": [8],
            "adds": {"1": 8},
            "drops": {"2": 8},
            "draft_picks": [],
            "settings": {"waiver_bid": 17},
        }
        rows = processor_handler.compile_sleeper_transactions(
            [(txn, "2024")], self._meta(), self._roster_map()
        )
        row = rows[0]
        assert row["season"] == "2024"
        assert row["type"] == "waiver"
        assert row["week"] == 1
        assert row["roster_ids"] == ["8"]
        assert row["teams"] == [
            {"roster_id": "8", "team_name": "Team Eight", "display_name": "user8"}
        ]
        assert row["adds"][0]["player_name"] == "Joe Burrow"
        assert row["drops"][0]["player_name"] == "Ja'Marr Chase"
        assert row["waiver_bid"] == 17

    def test_trade_with_draft_picks(self, processor_handler):
        txn = {
            "transaction_id": "t2",
            "type": "trade",
            "status": "complete",
            "leg": 1,
            "created": 200,
            "roster_ids": [1, 9],
            "adds": None,
            "drops": None,
            "draft_picks": [
                {
                    "round": 15,
                    "season": "2028",
                    "owner_id": 9,
                    "previous_owner_id": 1,
                }
            ],
            "settings": None,
        }
        rows = processor_handler.compile_sleeper_transactions(
            [(txn, "2024")], self._meta(), self._roster_map()
        )
        pick = rows[0]["draft_picks"][0]
        assert pick == {
            "round": 15,
            "season": "2028",
            "from_roster_id": "1",
            "to_roster_id": "9",
        }
        assert rows[0]["adds"] == []
        assert rows[0]["drops"] == []
        assert rows[0]["waiver_bid"] is None

    def test_free_agent_drop_only_and_unresolved_team(self, processor_handler):
        txn = {
            "transaction_id": "t3",
            "type": "free_agent",
            "status": "complete",
            "leg": 2,
            "created": 300,
            "roster_ids": [12],
            "adds": {"1": 12},
            "drops": None,
            "draft_picks": [],
            "settings": None,
        }
        rows = processor_handler.compile_sleeper_transactions(
            [(txn, "2024")], self._meta(), self._roster_map()
        )
        # roster 12 is not in the roster map → team labels fall back to null.
        assert rows[0]["teams"] == [
            {"roster_id": "12", "team_name": None, "display_name": None}
        ]
        assert rows[0]["drops"] == []
        assert len(rows[0]["adds"]) == 1


class TestDataframeToDynamoItems:
    def test_groups_rows_by_sk(self, processor_handler):
        con = duckdb.connect()
        df = pd.DataFrame(
            [
                {"season": "2024", "team_id": "1", "name": "Alice"},
                {"season": "2024", "team_id": "2", "name": "Bob"},
            ]
        )
        con.register("test_table", df)
        rel = con.sql("SELECT * FROM test_table")

        KeySchema = processor_handler.KeySchema
        schema = KeySchema(
            pk="LEAGUE#abc",
            sk=lambda row: f"TEAMS#{row['season']}",
            entity_type=processor_handler.EntityType.TEAMS,
        )

        items = processor_handler.dataframe_to_dynamo_items(rel, schema)
        assert len(items) == 1  # both rows have the same season -> same SK
        assert items[0]["PK"] == "LEAGUE#abc"
        assert "SK" in items[0]
        assert len(items[0]["data"]) == 2


class TestRegisterRawData:
    def test_raises_for_unsupported_platform(self, processor_handler):
        con = duckdb.connect()
        with pytest.raises(ValueError, match="Unsupported platform"):
            processor_handler.register_raw_data([], con, platform="YAHOO")


class TestBuildESPNBrackets:
    def test_empty_matchups_returns_empty(self, processor_handler):
        result = processor_handler._build_espn_brackets([])
        assert result == []

    def test_non_playoff_matchups_excluded(self, processor_handler):
        matchups = [
            {
                "season": "2024",
                "playoff_tier_type": "NONE",
                "week": "15",
                "team_a_id": 1,
                "team_b_id": 2,
                "team_a_score": "100",
                "team_b_score": "90",
                "winner": 1,
                "loser": 2,
            }
        ]
        result = processor_handler._build_espn_brackets(matchups)
        assert result == []

    def test_playoff_matchups_create_bracket_entries(self, processor_handler):
        matchups = [
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
                "week": 15,
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": 1,
                "loser": 2,
            },
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
                "week": 16,
                "team_a_id": 1,
                "team_b_id": 3,
                "winner": 1,
                "loser": 3,
            },
        ]
        result = processor_handler._build_espn_brackets(matchups)
        assert len(result) == 2
        final_entry = next(e for e in result if e["round"] == 2)
        assert final_entry["position"] == 1  # WB final = championship

    def test_bye_matchups_skipped(self, processor_handler):
        matchups = [
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
                "week": 15,
                "team_a_id": 1,
                "team_b_id": "",  # bye
                "winner": "",
                "loser": "",
            }
        ]
        result = processor_handler._build_espn_brackets(matchups)
        assert result == []

    def test_consolation_final_position_set_correctly(self, processor_handler):
        matchups = [
            # Round 1: WB game
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
                "week": 15,
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": 1,
                "loser": 2,
            },
            # Round 2: consolation (loser of WB vs loser of WB -> 3rd place)
            {
                "season": "2024",
                "playoff_tier_type": "WINNERS_CONSOLATION_LADDER",
                "week": 16,
                "team_a_id": 2,
                "team_b_id": 3,
                "winner": 2,
                "loser": 3,
            },
        ]
        result = processor_handler._build_espn_brackets(matchups)
        consolation_final = next(
            (e for e in result if e["position"] is not None and e["round"] == 2), None
        )
        assert consolation_final is not None


class TestRegisterESPNRawData:
    def test_parses_users_and_teams(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "users",
                "data": {
                    "members": [{"id": "m1", "displayName": "Alice"}],
                    "teams": [{"id": 1, "primaryOwner": "m1", "season": "2024"}],
                },
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert len(result["members"]) == 1
        assert result["members"][0]["season"] == "2024"
        assert len(result["teams"]) == 1

    def test_parses_draft_picks(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "draft_picks",
                "data": {"draft_picks": [{"playerId": 100, "overallPickNumber": 1}]},
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert len(result["draft_picks"]) == 1
        assert result["draft_picks"][0]["season"] == "2024"

    def test_parses_player_scoring_totals(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "player_scoring_totals",
                "data": {
                    "player_scoring_totals": [
                        {
                            "player_id": 10,
                            "player_name": "Joe Burrow",
                            "position": 1,
                            "total_points": 300.0,
                        }
                    ]
                },
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert len(result["player_scoring_totals"]) == 1
        assert result["player_scoring_totals"][0]["position"] == "QB"

    def test_parses_settings_for_league_name(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "settings",
                "data": {"settings": {"name": "My League"}},
            }
        ]
        result = processor_handler._register_espn_raw_data(raw)
        assert result["league_name_by_season"]["2024"] == "My League"


class TestRegisterSleeperRawData:
    def test_parses_users(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "users",
                "data": [{"user_id": "u1", "display_name": "Alice"}],
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert len(result["users"]) == 1
        assert result["users"][0]["season"] == "2024"

    def test_parses_league_settings_name(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "league_settings",
                "data": {"name": "My Sleeper League", "scoring_settings": {}},
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["league_name_by_season"]["2024"] == "My Sleeper League"

    def test_parses_brackets(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [{"m": 1, "r": 1, "t1": 1, "t2": 2, "w": 1, "l": 2, "p": None}],
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert len(result["brackets"]) == 1

    def test_skips_bracket_entries_without_both_teams(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [{"m": 1, "r": 1, "t1": 1, "t2": None, "w": None, "l": None}],
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert len(result["brackets"]) == 0

    def test_parses_draft_picks(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "draft_picks",
                "data": [{"player_id": "p1", "round": 1, "pick_no": 1}],
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert len(result["draft_picks"]) == 1

    def test_losers_bracket_uses_losers_tier(self, processor_handler):
        raw = [
            {
                "season": "2024",
                "data_type": "losers_bracket",
                "data": [{"m": 1, "r": 1, "t1": 5, "t2": 6, "w": 5, "l": 6, "p": 1}],
            }
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["brackets"][0]["bracket_type"] == "LOSERS_BRACKET"

    def test_winners_consolation_tier_assigned_to_matchups(self, processor_handler):
        # Winners bracket: semifinals (m1, m2) feed the championship (m3, p=1);
        # their losers feed the 3rd-place game (m4, p=3).
        raw = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [
                    {"m": 1, "r": 1, "t1": 1, "t2": 4, "w": 1, "l": 4, "p": None},
                    {"m": 2, "r": 1, "t1": 2, "t2": 3, "w": 2, "l": 3, "p": None},
                    {
                        "m": 3,
                        "r": 2,
                        "t1": 1,
                        "t2": 2,
                        "w": 1,
                        "l": 2,
                        "p": 1,
                        "t1_from": {"w": 1},
                        "t2_from": {"w": 2},
                    },
                    {
                        "m": 4,
                        "r": 2,
                        "t1": 4,
                        "t2": 3,
                        "w": 4,
                        "l": 3,
                        "p": 3,
                        "t1_from": {"l": 1},
                        "t2_from": {"l": 2},
                    },
                ],
            },
            {
                "season": "2024",
                "data_type": "matchupsweek16",
                "data": [
                    {"matchup_id": 1, "roster_id": 1, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 2, "points": 90.0},
                    {"matchup_id": 2, "roster_id": 4, "points": 80.0},
                    {"matchup_id": 2, "roster_id": 3, "points": 70.0},
                ],
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        tiers = {
            frozenset([m["team_a_roster_id"], m["team_b_roster_id"]]): m[
                "playoff_tier_type"
            ]
            for m in result["matchups"]
        }
        assert tiers[frozenset([1, 2])] == "WINNERS_BRACKET"  # championship game
        assert tiers[frozenset([4, 3])] == "WINNERS_CONSOLATION_LADDER"  # 3rd place

    def test_winners_tier_with_partial_from_links(self, processor_handler):
        # 6-team bracket (teams 2 and 3 have round-1 byes) where Sleeper populates
        # t1_from/t2_from only on the final round. The early-round winners games
        # (m1, m2) must still be classified WINNERS_BRACKET — not consolation —
        # once the missing feeder links are reconstructed. m5 (5th) and m7 (3rd)
        # are the only consolation games.
        raw = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [
                    {"m": 1, "r": 1, "t1": 11, "t2": 7, "w": 11, "l": 7},
                    {"m": 2, "r": 1, "t1": 1, "t2": 5, "w": 5, "l": 1},
                    {"m": 3, "r": 2, "t1": 2, "t2": 11, "w": 11, "l": 2},
                    {"m": 4, "r": 2, "t1": 3, "t2": 5, "w": 3, "l": 5},
                    {"m": 5, "r": 2, "t1": 7, "t2": 1, "w": 7, "l": 1, "p": 5},
                    {
                        "m": 6,
                        "r": 3,
                        "t1": 11,
                        "t2": 3,
                        "w": 11,
                        "l": 3,
                        "p": 1,
                        "t1_from": {"w": 3},
                        "t2_from": {"w": 4},
                    },
                    {
                        "m": 7,
                        "r": 3,
                        "t1": 2,
                        "t2": 5,
                        "w": 5,
                        "l": 2,
                        "p": 3,
                        "t1_from": {"l": 3},
                        "t2_from": {"l": 4},
                    },
                ],
            },
            {
                "season": "2024",
                "data_type": "matchupsweek15",
                "data": [
                    {"matchup_id": 1, "roster_id": 11, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 7, "points": 90.0},
                    {"matchup_id": 2, "roster_id": 5, "points": 100.0},
                    {"matchup_id": 2, "roster_id": 1, "points": 90.0},
                ],
            },
            {
                "season": "2024",
                "data_type": "matchupsweek16",
                "data": [
                    {"matchup_id": 1, "roster_id": 11, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 2, "points": 90.0},
                    {"matchup_id": 2, "roster_id": 3, "points": 100.0},
                    {"matchup_id": 2, "roster_id": 5, "points": 90.0},
                    {"matchup_id": 3, "roster_id": 7, "points": 100.0},
                    {"matchup_id": 3, "roster_id": 1, "points": 90.0},
                ],
            },
            {
                "season": "2024",
                "data_type": "matchupsweek17",
                "data": [
                    {"matchup_id": 1, "roster_id": 11, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 3, "points": 90.0},
                    {"matchup_id": 2, "roster_id": 5, "points": 100.0},
                    {"matchup_id": 2, "roster_id": 2, "points": 90.0},
                ],
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        tiers = {
            frozenset([m["team_a_roster_id"], m["team_b_roster_id"]]): m[
                "playoff_tier_type"
            ]
            for m in result["matchups"]
        }
        # Round-1 winners games (previously mislabelled consolation) and the
        # semifinals/championship are all WINNERS_BRACKET.
        assert tiers[frozenset([11, 7])] == "WINNERS_BRACKET"
        assert tiers[frozenset([1, 5])] == "WINNERS_BRACKET"
        assert tiers[frozenset([2, 11])] == "WINNERS_BRACKET"
        assert tiers[frozenset([3, 5])] == "WINNERS_BRACKET"
        assert tiers[frozenset([11, 3])] == "WINNERS_BRACKET"
        # The genuine consolation games.
        assert tiers[frozenset([7, 1])] == "WINNERS_CONSOLATION_LADDER"  # 5th place
        assert tiers[frozenset([2, 5])] == "WINNERS_CONSOLATION_LADDER"  # 3rd place

        # The emitted bracket rows carry the reconstructed feeder links: each
        # semifinal's played team points back to its round-1 game, while the bye
        # team keeps a null link so the frontend renders its bye card.
        brackets = {b["match_id"]: b for b in result["brackets"]}
        assert brackets[3]["team_1_from"] is None  # team 2 had a bye
        assert json.loads(brackets[3]["team_2_from"]) == {"w": 1}  # team 11 from m1
        assert brackets[4]["team_1_from"] is None  # team 3 had a bye
        assert json.loads(brackets[4]["team_2_from"]) == {"w": 2}  # team 5 from m2

    def test_playoff_week_start_keeps_week_15_regular_season(self, processor_handler):
        # League with a 15-week regular season (playoffs start week 16): the
        # week-15 game must be regular season, not defaulted to LOSERS_BRACKET.
        raw = [
            {
                "season": "2024",
                "data_type": "league_settings",
                "data": {"settings": {"playoff_week_start": 16}},
            },
            {
                "season": "2024",
                "data_type": "matchupsweek15",
                "data": [
                    {"matchup_id": 1, "roster_id": 1, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 2, "points": 90.0},
                ],
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["matchups"][0]["playoff_tier_type"] == "NONE"

    def test_playoff_week_start_classifies_first_playoff_week(self, processor_handler):
        # With playoffs starting week 16, a week-16 winners-bracket game is
        # classified from the bracket, not suppressed to NONE.
        raw = [
            {
                "season": "2024",
                "data_type": "league_settings",
                "data": {"settings": {"playoff_week_start": 16}},
            },
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [{"m": 1, "r": 1, "t1": 1, "t2": 2, "w": 1, "l": 2, "p": 1}],
            },
            {
                "season": "2024",
                "data_type": "matchupsweek16",
                "data": [
                    {"matchup_id": 1, "roster_id": 1, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 2, "points": 90.0},
                ],
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["matchups"][0]["playoff_tier_type"] == "WINNERS_BRACKET"

    def test_missing_playoff_week_start_falls_back_to_default(self, processor_handler):
        # No playoff_week_start available: season >= 2021 falls back to week 15, so a
        # week-15 game is postseason. The season has a bracket (a different pair), but this
        # game's pair is not in it, so it falls back to LOSERS_BRACKET (a consolation game).
        raw = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [{"m": 1, "r": 1, "t1": 3, "t2": 4, "w": 3, "l": 4, "p": 1}],
            },
            {
                "season": "2024",
                "data_type": "matchupsweek15",
                "data": [
                    {"matchup_id": 1, "roster_id": 1, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 2, "points": 90.0},
                ],
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert result["matchups"][0]["playoff_tier_type"] == "LOSERS_BRACKET"

    def test_playoff_weeks_without_any_bracket_are_regular_season(
        self, processor_handler
    ):
        # A season with no playoff bracket at all (e.g. the Sleeper bracket endpoints
        # returned null) must not default its playoff-week games to LOSERS_BRACKET — with
        # no bracket to classify them, they stay regular-season (NONE).
        raw = [
            {
                "season": "2024",
                "data_type": "matchupsweek15",
                "data": [
                    {"matchup_id": 1, "roster_id": 1, "points": 100.0},
                    {"matchup_id": 1, "roster_id": 2, "points": 90.0},
                ],
            },
            {
                "season": "2024",
                "data_type": "matchupsweek16",
                "data": [
                    {"matchup_id": 1, "roster_id": 1, "points": 110.0},
                    {"matchup_id": 1, "roster_id": 2, "points": 95.0},
                ],
            },
        ]
        result = processor_handler._register_sleeper_raw_data(raw, {}, {})
        assert {m["playoff_tier_type"] for m in result["matchups"]} == {"NONE"}


class TestTraceSleeperChampionshipPath:
    def test_excludes_consolation_games(self, processor_handler):
        entries = [
            {"m": 1, "r": 1, "t1": 1, "t2": 4, "p": None},
            {"m": 2, "r": 1, "t1": 2, "t2": 3, "p": None},
            {
                "m": 3,
                "r": 2,
                "t1": 1,
                "t2": 2,
                "p": 1,
                "t1_from": {"w": 1},
                "t2_from": {"w": 2},
            },
            {
                "m": 4,
                "r": 2,
                "t1": 4,
                "t2": 3,
                "p": 3,
                "t1_from": {"l": 1},
                "t2_from": {"l": 2},
            },
        ]
        path = processor_handler._trace_sleeper_championship_path(entries)
        assert path == {1, 2, 3}  # 3rd-place game (m4) excluded

    def test_returns_none_without_championship_game(self, processor_handler):
        entries = [{"m": 1, "r": 1, "t1": 1, "t2": 2, "p": None}]
        assert processor_handler._trace_sleeper_championship_path(entries) is None


class TestBackfillSleeperFromLinks:
    def test_reconstructs_absent_winner_link(self, processor_handler):
        # A round-2 game with no from-links: the played team points back to the
        # round-1 game it won; the bye team gets no link at all.
        entries = [
            {"m": 1, "r": 1, "t1": 11, "t2": 7, "w": 11, "l": 7},
            {"m": 3, "r": 2, "t1": 2, "t2": 11, "w": 11, "l": 2},
        ]
        processor_handler._backfill_sleeper_from_links(entries)
        semi = entries[1]
        assert semi["t2_from"] == {"w": 1}  # team 11 came from winning m1
        assert "t1_from" not in semi  # team 2 had a bye

    def test_reconstructs_loser_fed_link(self, processor_handler):
        # A consolation game fed by two round-1 losers points back with {"l": ...}.
        entries = [
            {"m": 1, "r": 1, "t1": 11, "t2": 7, "w": 11, "l": 7},
            {"m": 2, "r": 1, "t1": 1, "t2": 5, "w": 5, "l": 1},
            {"m": 5, "r": 2, "t1": 7, "t2": 1, "w": 7, "l": 1, "p": 5},
        ]
        processor_handler._backfill_sleeper_from_links(entries)
        consolation = entries[2]
        assert consolation["t1_from"] == {"l": 1}  # team 7 lost m1
        assert consolation["t2_from"] == {"l": 2}  # team 1 lost m2

    def test_preserves_existing_links(self, processor_handler):
        # Links Sleeper already provided are never overwritten.
        entries = [
            {"m": 3, "r": 2, "t1": 2, "t2": 11, "w": 11, "l": 2},
            {"m": 4, "r": 2, "t1": 3, "t2": 5, "w": 3, "l": 5},
            {
                "m": 6,
                "r": 3,
                "t1": 11,
                "t2": 3,
                "w": 11,
                "l": 3,
                "p": 1,
                "t1_from": {"w": 3},
                "t2_from": {"w": 4},
            },
        ]
        processor_handler._backfill_sleeper_from_links(entries)
        final = entries[2]
        assert final["t1_from"] == {"w": 3}
        assert final["t2_from"] == {"w": 4}

    def test_round_one_untouched(self, processor_handler):
        entries = [{"m": 1, "r": 1, "t1": 11, "t2": 7, "w": 11, "l": 7}]
        processor_handler._backfill_sleeper_from_links(entries)
        assert "t1_from" not in entries[0]
        assert "t2_from" not in entries[0]

    def test_skips_entries_missing_ids_or_ties(self, processor_handler):
        # An entry without m/r contributes no result, and a TIE winner/loser is not
        # recorded, so a later round finds no feeder link to reconstruct.
        entries = [
            {"m": None, "r": None, "t1": 11, "t2": 7, "w": 11, "l": 7},
            {"m": 2, "r": 1, "t1": 1, "t2": 5, "w": "TIE", "l": "TIE"},
            {"m": 3, "r": 2, "t1": 1, "t2": 11, "w": 1, "l": 11},
        ]
        processor_handler._backfill_sleeper_from_links(entries)
        semi = entries[2]
        assert "t1_from" not in semi  # team 1 tied m2, no result recorded
        assert "t2_from" not in semi  # team 11's round-1 game had no match id


class TestWriteMetadataItems:
    def test_refresh_marks_job_completed_no_status_on_metadata(self, processor_handler):
        # Job status now lives in the JOB_STATUS item; METADATA carries no status.
        mock_ddb = MagicMock()
        with (
            patch.object(processor_handler, "ddb_client", mock_ddb),
            patch.object(processor_handler, "write_job_status") as mock_write_job,
        ):
            processor_handler.write_metadata_items(
                league_id="canonical-abc", refresh=True
            )
        item = mock_ddb.transact_write_items.call_args[1]["TransactItems"][0]["Update"]
        assert "refresh_status" not in item["UpdateExpression"]
        assert "onboarding_status" not in item["UpdateExpression"]
        mock_write_job.assert_called_once()
        assert mock_write_job.call_args[0][1] == "COMPLETED"

    def test_onboard_marks_job_completed_without_metadata_write(
        self, processor_handler
    ):
        # A plain onboard (no refresh, no league_name) has nothing to write to
        # METADATA, so only the JOB_STATUS COMPLETED write happens.
        mock_ddb = MagicMock()
        with (
            patch.object(processor_handler, "ddb_client", mock_ddb),
            patch.object(processor_handler, "write_job_status") as mock_write_job,
        ):
            processor_handler.write_metadata_items(
                league_id="canonical-abc", refresh=False
            )
        mock_ddb.transact_write_items.assert_not_called()
        mock_write_job.assert_called_once()
        assert mock_write_job.call_args[0][1] == "COMPLETED"

    def test_refresh_writes_last_refresh_at(self, processor_handler):
        mock_ddb = MagicMock()
        with (
            patch.object(processor_handler, "ddb_client", mock_ddb),
            patch.object(processor_handler, "write_job_status"),
        ):
            processor_handler.write_metadata_items(
                league_id="canonical-abc", refresh=True
            )
        item = mock_ddb.transact_write_items.call_args[1]["TransactItems"][0]["Update"]
        assert "last_refresh_at" in item["UpdateExpression"]
        assert ":lra" in item["ExpressionAttributeValues"]
        assert item["ExpressionAttributeValues"][":lra"]["S"]  # non-empty ISO string

    def test_league_name_included_when_provided(self, processor_handler):
        mock_ddb = MagicMock()
        with patch.object(processor_handler, "ddb_client", mock_ddb):
            processor_handler.write_metadata_items(
                league_id="canonical-abc", refresh=True, league_name="Test League"
            )
        item = mock_ddb.transact_write_items.call_args[1]["TransactItems"][0]["Update"]
        assert "league_name" in item["UpdateExpression"]
        assert item["ExpressionAttributeValues"][":league_name"] == {"S": "Test League"}

    def test_league_name_omitted_when_not_provided(self, processor_handler):
        mock_ddb = MagicMock()
        with patch.object(processor_handler, "ddb_client", mock_ddb):
            processor_handler.write_metadata_items(
                league_id="canonical-abc", refresh=True
            )
        item = mock_ddb.transact_write_items.call_args[1]["TransactItems"][0]["Update"]
        assert "league_name" not in item["UpdateExpression"]
        assert ":league_name" not in item["ExpressionAttributeValues"]


class TestLambdaHandlerFailure:
    def test_records_failed_job_and_reraises(self, processor_handler):
        with (
            patch.object(
                processor_handler,
                "_lambda_handler_impl",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(processor_handler, "publish_failure") as mock_pf,
            patch.object(processor_handler, "write_job_status") as mock_wjs,
            pytest.raises(RuntimeError),
        ):
            processor_handler.lambda_handler({}, MagicMock())
        mock_pf.assert_called_once()
        mock_wjs.assert_called_once()
        args, kwargs = mock_wjs.call_args
        assert args[1] == "FAILED"
        assert kwargs["failure_code"] == "PROCESSING"


class TestUpdateLeagueCount:
    def test_increments_count(self, processor_handler):
        mock_ddb = MagicMock()
        with patch.object(processor_handler, "ddb_client", mock_ddb):
            processor_handler.update_league_count(1)
        mock_ddb.update_item.assert_called_once_with(
            TableName=processor_handler.table.name,
            Key={"PK": {"S": "APP#STATS"}, "SK": {"S": "LEAGUE_COUNT"}},
            UpdateExpression="ADD league_count :delta",
            ExpressionAttributeValues={":delta": {"N": "1"}},
        )

    def test_decrements_count(self, processor_handler):
        mock_ddb = MagicMock()
        with patch.object(processor_handler, "ddb_client", mock_ddb):
            processor_handler.update_league_count(-1)
        mock_ddb.update_item.assert_called_once_with(
            TableName=processor_handler.table.name,
            Key={"PK": {"S": "APP#STATS"}, "SK": {"S": "LEAGUE_COUNT"}},
            UpdateExpression="ADD league_count :delta",
            ExpressionAttributeValues={":delta": {"N": "-1"}},
        )


def _draft_pick(player_id, team_id, season, bid, overall_pick, position_slot=2):
    """Build a single ESPN draft_picks row with all columns the query reads."""
    return {
        "id": player_id,
        "teamId": team_id,
        "season": season,
        "playerId": player_id,
        "bidAmount": bid,
        "overallPickNumber": overall_pick,
        "roundId": 1,
        "roundPickNumber": overall_pick,
        "keeper": False,
        "reservedForKeeper": False,
        "autoDraftTypeId": 0,
        "lineupSlotId": position_slot,
        "memberId": f"member-{player_id}",
        "nominatingTeamId": 0,
        "tradeLocked": False,
    }


class TestEspnDraftRankCalculation:
    """End-to-end checks of QUERIES['DRAFT']['ESPN'] for auction vs. snake seasons."""

    def _run_query(self, processor_handler, draft_picks, scoring, teams):
        con = duckdb.connect()
        con.register("draft_picks", pd.DataFrame(draft_picks))
        con.register("player_scoring_totals", pd.DataFrame(scoring))
        con.register("teams_output", pd.DataFrame(teams))
        rel = con.sql(processor_handler.QUERIES["DRAFT"]["ESPN"])
        rows = {r["player_id"]: r for r in rel.df().to_dict("records")}
        con.close()
        return rows

    def test_auction_season_ranks_by_bid_amount(self, processor_handler):
        # 2024 is an auction season: highest bid wins, nomination order is noise.
        # The highest-bid RB is nominated LAST (overall pick 3) to prove the rank
        # comes from bidAmount, not overallPickNumber.
        draft_picks = [
            _draft_pick(1, 8, "2024", bid=50, overall_pick=3),
            _draft_pick(2, 9, "2024", bid=30, overall_pick=1),
            _draft_pick(3, 8, "2024", bid=30, overall_pick=2),
        ]
        scoring = [
            {
                "player_id": 1,
                "season": "2024",
                "player_name": "RB One",
                "position": "RB",
                "total_points": 200.0,
            },
            {
                "player_id": 2,
                "season": "2024",
                "player_name": "RB Two",
                "position": "RB",
                "total_points": 150.0,
            },
            {
                "player_id": 3,
                "season": "2024",
                "player_name": "RB Three",
                "position": "RB",
                "total_points": 100.0,
            },
        ]
        teams = [
            {
                "team_id": "8",
                "season": "2024",
                "display_name": "u8",
                "team_name": "T8",
                "team_logo": "l8",
            },
            {
                "team_id": "9",
                "season": "2024",
                "display_name": "u9",
                "team_name": "T9",
                "team_logo": "l9",
            },
        ]

        rows = self._run_query(processor_handler, draft_picks, scoring, teams)

        assert all(r["is_auction"] for r in rows.values())
        # Highest bid -> drafted rank 1 despite being nominated last.
        assert rows["1"]["drafted_position_rank"] == 1
        # Equal bids share a rank (RANK semantics, no tiebreak).
        assert rows["2"]["drafted_position_rank"] == 2
        assert rows["3"]["drafted_position_rank"] == 2
        # delta = drafted - actual position rank.
        assert rows["1"]["draft_rank_delta"] == 0
        assert rows["2"]["draft_rank_delta"] == 0
        assert rows["3"]["draft_rank_delta"] == -1

    def test_snake_season_ranks_by_overall_pick(self, processor_handler):
        # 2023 has no bids -> snake season -> rank by overallPickNumber.
        draft_picks = [
            _draft_pick(10, 8, "2023", bid=0, overall_pick=1),
            _draft_pick(11, 9, "2023", bid=0, overall_pick=2),
        ]
        scoring = [
            {
                "player_id": 10,
                "season": "2023",
                "player_name": "WR One",
                "position": "WR",
                "total_points": 300.0,
            },
            {
                "player_id": 11,
                "season": "2023",
                "player_name": "WR Two",
                "position": "WR",
                "total_points": 250.0,
            },
        ]
        teams = [
            {
                "team_id": "8",
                "season": "2023",
                "display_name": "u8",
                "team_name": "T8",
                "team_logo": "l8",
            },
            {
                "team_id": "9",
                "season": "2023",
                "display_name": "u9",
                "team_name": "T9",
                "team_logo": "l9",
            },
        ]

        rows = self._run_query(processor_handler, draft_picks, scoring, teams)

        assert not any(r["is_auction"] for r in rows.values())
        assert rows["10"]["drafted_position_rank"] == 1
        assert rows["11"]["drafted_position_rank"] == 2


def _sleeper_draft_pick(player_id, roster_id, season, pick_no, position, bid=None):
    """Build a single Sleeper draft_picks row with the columns the query reads.

    Pass ``bid`` to make it an auction pick — Sleeper stores the winning bid as a
    string in ``metadata.amount`` and omits the key entirely for snake drafts.
    """
    metadata = {
        "first_name": f"First{player_id}",
        "last_name": f"Last{player_id}",
        "position": position,
    }
    if bid is not None:
        metadata["amount"] = str(bid)
    return {
        "player_id": player_id,
        "roster_id": roster_id,
        "season": season,
        "pick_no": pick_no,
        "round": 1,
        "draft_slot": pick_no,
        "is_keeper": False,
        "picked_by": f"member-{player_id}",
        "metadata": metadata,
    }


class TestSleeperDraftRankCalculation:
    """End-to-end checks of QUERIES['DRAFT']['SLEEPER'] for auction vs. snake seasons."""

    def _run_query(self, processor_handler, draft_picks, scoring, teams):
        con = duckdb.connect()
        con.register("draft_picks", pd.DataFrame(draft_picks))
        con.register("player_scoring_totals", pd.DataFrame(scoring))
        con.register("teams_output", pd.DataFrame(teams))
        rel = con.sql(processor_handler.QUERIES["DRAFT"]["SLEEPER"])
        rows = {r["player_id"]: r for r in rel.df().to_dict("records")}
        con.close()
        return rows

    def test_auction_season_ranks_by_bid_amount(self, processor_handler):
        # 2024 is an auction season: highest bid wins, nomination order is noise.
        # The highest-bid RB is nominated LAST (pick_no 3) to prove the rank comes
        # from metadata.amount, not pick_no.
        draft_picks = [
            _sleeper_draft_pick("1", "8", "2024", pick_no=3, position="RB", bid=50),
            _sleeper_draft_pick("2", "9", "2024", pick_no=1, position="RB", bid=30),
            _sleeper_draft_pick("3", "8", "2024", pick_no=2, position="RB", bid=30),
        ]
        scoring = [
            {
                "player_id": "1",
                "season": "2024",
                "player_name": "RB One",
                "position": "RB",
                "total_points": 200.0,
            },
            {
                "player_id": "2",
                "season": "2024",
                "player_name": "RB Two",
                "position": "RB",
                "total_points": 150.0,
            },
            {
                "player_id": "3",
                "season": "2024",
                "player_name": "RB Three",
                "position": "RB",
                "total_points": 100.0,
            },
        ]
        teams = [
            {
                "team_id": "8",
                "season": "2024",
                "display_name": "u8",
                "team_name": "T8",
                "team_logo": "l8",
            },
            {
                "team_id": "9",
                "season": "2024",
                "display_name": "u9",
                "team_name": "T9",
                "team_logo": "l9",
            },
        ]

        rows = self._run_query(processor_handler, draft_picks, scoring, teams)

        assert all(r["is_auction"] for r in rows.values())
        # The bid amount is surfaced from metadata.amount.
        assert rows["1"]["bid_amount"] == 50
        assert rows["2"]["bid_amount"] == 30
        # Highest bid -> drafted rank 1 despite being nominated last.
        assert rows["1"]["drafted_position_rank"] == 1
        # Equal bids share a rank (RANK semantics, no tiebreak).
        assert rows["2"]["drafted_position_rank"] == 2
        assert rows["3"]["drafted_position_rank"] == 2
        # delta = drafted - actual position rank.
        assert rows["1"]["draft_rank_delta"] == 0
        assert rows["2"]["draft_rank_delta"] == 0
        assert rows["3"]["draft_rank_delta"] == -1

    def test_snake_season_ranks_by_pick_no(self, processor_handler):
        # 2023 has no bids -> snake season -> rank by pick_no, bid_amount is null.
        draft_picks = [
            _sleeper_draft_pick("10", "8", "2023", pick_no=1, position="WR"),
            _sleeper_draft_pick("11", "9", "2023", pick_no=2, position="WR"),
        ]
        scoring = [
            {
                "player_id": "10",
                "season": "2023",
                "player_name": "WR One",
                "position": "WR",
                "total_points": 300.0,
            },
            {
                "player_id": "11",
                "season": "2023",
                "player_name": "WR Two",
                "position": "WR",
                "total_points": 250.0,
            },
        ]
        teams = [
            {
                "team_id": "8",
                "season": "2023",
                "display_name": "u8",
                "team_name": "T8",
                "team_logo": "l8",
            },
            {
                "team_id": "9",
                "season": "2023",
                "display_name": "u9",
                "team_name": "T9",
                "team_logo": "l9",
            },
        ]

        rows = self._run_query(processor_handler, draft_picks, scoring, teams)

        assert not any(r["is_auction"] for r in rows.values())
        assert pd.isna(rows["10"]["bid_amount"])
        assert rows["10"]["drafted_position_rank"] == 1
        assert rows["11"]["drafted_position_rank"] == 2
