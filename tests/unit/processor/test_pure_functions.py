"""Tests for pure functions in processor/handler.py."""

from decimal import Decimal

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
        stats, ids = processor_handler.compile_espn_starter_stats(roster, slot_map)
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
        stats, ids = processor_handler.compile_espn_starter_stats(roster, slot_map={})
        assert stats[0]["fantasy_position"] == "WR"

    def test_empty_roster(self, processor_handler):
        stats, ids = processor_handler.compile_espn_starter_stats({}, {})
        assert stats == []
        assert ids == []


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
