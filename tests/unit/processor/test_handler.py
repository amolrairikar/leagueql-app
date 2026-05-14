"""Tests for processor/handler.py."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import botocore.exceptions
import duckdb
import pandas as pd
import pytest


class TestCompileEspnBenchStats:
    def test_excludes_starter_ids(self):
        from handler import compile_espn_bench_stats

        roster = {
            "entries": [
                {
                    "playerId": 1,
                    "playerPoolEntry": {
                        "player": {"fullName": "QB1", "defaultPositionId": 1},
                        "appliedStatTotal": 30.0,
                    },
                },
                {
                    "playerId": 2,
                    "playerPoolEntry": {
                        "player": {"fullName": "RB1", "defaultPositionId": 2},
                        "appliedStatTotal": 18.5,
                    },
                },
            ]
        }
        result = compile_espn_bench_stats(roster, starter_ids=[1])
        assert len(result) == 1
        assert result[0]["player_id"] == 2
        assert result[0]["full_name"] == "RB1"
        assert result[0]["points_scored"] == 18.5
        assert result[0]["position"] == "RB"

    def test_empty_roster_returns_empty_list(self):
        from handler import compile_espn_bench_stats

        result = compile_espn_bench_stats({}, starter_ids=[])
        assert result == []

    def test_all_players_are_starters_returns_empty(self):
        from handler import compile_espn_bench_stats

        roster = {
            "entries": [
                {
                    "playerId": 1,
                    "playerPoolEntry": {
                        "player": {"fullName": "QB1", "defaultPositionId": 1},
                        "appliedStatTotal": 25.0,
                    },
                }
            ]
        }
        result = compile_espn_bench_stats(roster, starter_ids=[1])
        assert result == []

    def test_unknown_position_returns_none(self):
        from handler import compile_espn_bench_stats

        roster = {
            "entries": [
                {
                    "playerId": 99,
                    "playerPoolEntry": {
                        "player": {"fullName": "Unknown", "defaultPositionId": 99},
                        "appliedStatTotal": 5.0,
                    },
                }
            ]
        }
        result = compile_espn_bench_stats(roster, starter_ids=[])
        assert result[0]["position"] is None


class TestCompileEspnStarterStats:
    def test_uses_slot_map_for_fantasy_position(self):
        from handler import compile_espn_starter_stats

        roster = {
            "entries": [
                {
                    "playerId": 1,
                    "lineupSlotId": 0,
                    "playerPoolEntry": {
                        "player": {
                            "fullName": "Patrick Mahomes",
                            "defaultPositionId": 1,
                            "eligibleSlots": [0],
                        },
                        "appliedStatTotal": 35.0,
                    },
                }
            ]
        }
        stats, ids = compile_espn_starter_stats(roster, slot_map={1: 0})
        assert len(stats) == 1
        assert stats[0]["player_id"] == 1
        assert stats[0]["full_name"] == "Patrick Mahomes"
        assert stats[0]["fantasy_position"] == "QB"
        assert stats[0]["position"] == "QB"
        assert ids == [1]

    def test_falls_back_to_eligible_slots(self):
        from handler import compile_espn_starter_stats

        roster = {
            "entries": [
                {
                    "playerId": 2,
                    "lineupSlotId": 99,
                    "playerPoolEntry": {
                        "player": {
                            "fullName": "WR Player",
                            "defaultPositionId": 3,
                            "eligibleSlots": [4],
                        },
                        "appliedStatTotal": 20.0,
                    },
                }
            ]
        }
        stats, ids = compile_espn_starter_stats(roster, slot_map={})
        assert stats[0]["fantasy_position"] == "WR"

    def test_empty_roster_returns_empty(self):
        from handler import compile_espn_starter_stats

        stats, ids = compile_espn_starter_stats({}, slot_map={})
        assert stats == []
        assert ids == []


class TestCompileSleeperStarterStats:
    def test_basic_stats(self):
        from handler import compile_sleeper_starter_stats

        starters = ["123", "456"]
        starters_points = [25.5, 18.0]
        player_metadata = {
            "123": {"first_name": "Patrick", "last_name": "Mahomes", "position": "QB"},
            "456": {"first_name": "Tyreek", "last_name": "Hill", "position": "WR"},
        }
        stats, ids = compile_sleeper_starter_stats(
            starters, starters_points, player_metadata
        )
        assert len(stats) == 2
        assert stats[0]["full_name"] == "Patrick Mahomes"
        assert stats[0]["points_scored"] == 25.5
        assert stats[0]["position"] == "QB"
        assert ids == starters

    def test_def_position_converted_to_dst(self):
        from handler import compile_sleeper_starter_stats

        starters = ["789"]
        starters_points = [15.0]
        player_metadata = {
            "789": {
                "first_name": "Kansas City",
                "last_name": "Chiefs",
                "position": "DEF",
            }
        }
        stats, _ = compile_sleeper_starter_stats(
            starters, starters_points, player_metadata
        )
        assert stats[0]["position"] == "D/ST"

    def test_missing_metadata_uses_empty_strings(self):
        from handler import compile_sleeper_starter_stats

        stats, _ = compile_sleeper_starter_stats(["999"], [10.0], {})
        assert stats[0]["full_name"] == ""
        assert stats[0]["position"] is None


class TestCompileSleeperBenchStats:
    def test_excludes_starter_ids(self):
        from handler import compile_sleeper_bench_stats

        players = ["123", "456", "789"]
        players_points = {"123": 25.5, "456": 18.0, "789": 10.0}
        starter_ids = ["123", "456"]
        player_metadata = {
            "789": {"first_name": "Justin", "last_name": "Jefferson", "position": "WR"}
        }
        result = compile_sleeper_bench_stats(
            players, players_points, starter_ids, player_metadata
        )
        assert len(result) == 1
        assert result[0]["player_id"] == "789"
        assert result[0]["points_scored"] == 10.0
        assert result[0]["position"] == "WR"

    def test_def_converted_to_dst(self):
        from handler import compile_sleeper_bench_stats

        players = ["def1"]
        players_points = {"def1": 12.0}
        player_metadata = {
            "def1": {"first_name": "Dallas", "last_name": "Cowboys", "position": "DEF"}
        }
        result = compile_sleeper_bench_stats(
            players, players_points, [], player_metadata
        )
        assert result[0]["position"] == "D/ST"

    def test_missing_points_defaults_to_zero(self):
        from handler import compile_sleeper_bench_stats

        players = ["123"]
        player_metadata = {
            "123": {"first_name": "A", "last_name": "B", "position": "RB"}
        }
        result = compile_sleeper_bench_stats(players, {}, [], player_metadata)
        assert result[0]["points_scored"] == 0.0


class TestCompileSleeperPlayerScoringTotals:
    def test_calculates_total_points(self):
        from handler import compile_sleeper_player_scoring_totals

        player_stats = {"123": {"2024": {"rush_yd": 100, "rush_td": 1}}}
        scoring_settings_by_season = {"2024": {"rush_yd": 0.1, "rush_td": 6.0}}
        player_metadata = {
            "123": {"first_name": "Derrick", "last_name": "Henry", "position": "RB"}
        }
        result = compile_sleeper_player_scoring_totals(
            player_stats, scoring_settings_by_season, player_metadata
        )
        assert len(result) == 1
        assert result[0]["player_id"] == "123"
        assert result[0]["total_points"] == pytest.approx(16.0)
        assert result[0]["season"] == "2024"
        assert result[0]["position"] == "RB"

    def test_skips_season_not_in_player_stats(self):
        from handler import compile_sleeper_player_scoring_totals

        player_stats = {"123": {"2023": {"rush_yd": 100}}}
        scoring_settings_by_season = {"2024": {"rush_yd": 0.1}}
        player_metadata = {
            "123": {"first_name": "A", "last_name": "B", "position": "RB"}
        }
        result = compile_sleeper_player_scoring_totals(
            player_stats, scoring_settings_by_season, player_metadata
        )
        assert result == []

    def test_def_position_converted(self):
        from handler import compile_sleeper_player_scoring_totals

        player_stats = {"def1": {"2024": {"pts_allow": 10}}}
        scoring_settings_by_season = {"2024": {"pts_allow": 2.0}}
        player_metadata = {
            "def1": {"first_name": "KC", "last_name": "Defense", "position": "DEF"}
        }
        result = compile_sleeper_player_scoring_totals(
            player_stats, scoring_settings_by_season, player_metadata
        )
        assert result[0]["position"] == "D/ST"

    def test_empty_player_stats_returns_empty_list(self):
        from handler import compile_sleeper_player_scoring_totals

        result = compile_sleeper_player_scoring_totals({}, {"2024": {}}, {})
        assert result == []


class TestSanitizeValue:
    @pytest.mark.parametrize(
        "val,expected",
        [
            (1.5, Decimal("1.5")),
            (42, 42),
            ("hello", "hello"),
            (None, None),
            ([1.5, 2], [Decimal("1.5"), 2]),
            ({"a": 1.5, "b": "x"}, {"a": Decimal("1.5"), "b": "x"}),
        ],
    )
    def test_sanitize_value(self, val, expected):
        from handler import sanitize_value

        assert sanitize_value(val) == expected

    def test_nested_dict_and_list(self):
        from handler import sanitize_value

        result = sanitize_value({"outer": [1.5, {"inner": 2.5}]})
        assert result == {"outer": [Decimal("1.5"), {"inner": Decimal("2.5")}]}


class TestResolveSeasons:
    @pytest.mark.parametrize(
        "current,previous,expected",
        [
            (["2022", "2023", "2024"], None, ["2022", "2023", "2024"]),
            (["2022", "2023", "2024"], ["2022", "2023"], ["2024"]),
            (["2022", "2023", "2024"], ["2022", "2023", "2024"], ["2024"]),
            (
                ["2022", "2023", "2024", "2025"],
                ["2022", "2023"],
                ["2024", "2025"],
            ),
        ],
    )
    def test_resolve_seasons(self, current, previous, expected):
        from handler import resolve_seasons_to_process

        result = resolve_seasons_to_process(current, previous)
        assert sorted(result) == sorted(expected)

    def test_initial_onboard_returns_all(self):
        from handler import resolve_seasons_to_process

        seasons = ["2021", "2022", "2023"]
        assert resolve_seasons_to_process(seasons, None) == seasons


class TestBuildEspnBracketsTeamBWins:
    def test_team_b_wins_updates_round_result(self):
        from handler import _build_espn_brackets

        matchups = [
            {
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": 2,
                "loser": 1,
                "week": "15",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
            {
                "team_a_id": 3,
                "team_b_id": 4,
                "winner": 3,
                "loser": 4,
                "week": "15",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
            {
                "team_a_id": 2,
                "team_b_id": 3,
                "winner": 2,
                "loser": 3,
                "week": "16",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
        ]
        result = _build_espn_brackets(matchups)
        final = next(e for e in result if e["round"] == 2)
        assert final["team_1"] == "2" or final["team_2"] == "2"
        assert final["team_1_from"] is not None or final["team_2_from"] is not None


class TestBuildEspnBrackets:
    def test_empty_input_returns_empty(self):
        from handler import _build_espn_brackets

        assert _build_espn_brackets([]) == []

    def test_skips_non_playoff_matchups(self):
        from handler import _build_espn_brackets

        matchups = [
            {
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": 1,
                "loser": 2,
                "week": "10",
                "season": "2024",
                "playoff_tier_type": "NONE",
            }
        ]
        assert _build_espn_brackets(matchups) == []

    def test_skips_bye_matchups(self):
        from handler import _build_espn_brackets

        matchups = [
            {
                "team_a_id": 1,
                "team_b_id": "",
                "winner": 1,
                "loser": "",
                "week": "15",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            }
        ]
        assert _build_espn_brackets(matchups) == []

    def test_championship_position_assigned_to_wb_final(self):
        from handler import _build_espn_brackets

        matchups = [
            {
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": 1,
                "loser": 2,
                "week": "15",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
            {
                "team_a_id": 3,
                "team_b_id": 4,
                "winner": 3,
                "loser": 4,
                "week": "15",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
            {
                "team_a_id": 1,
                "team_b_id": 3,
                "winner": 1,
                "loser": 3,
                "week": "16",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
            {
                "team_a_id": 2,
                "team_b_id": 4,
                "winner": 2,
                "loser": 4,
                "week": "16",
                "season": "2024",
                "playoff_tier_type": "WINNERS_CONSOLATION_LADDER",
            },
        ]
        result = _build_espn_brackets(matchups)
        finals = [e for e in result if e["round"] == 2]
        wb_final = next(e for e in finals if e["position"] == 1)
        consolation_final = next(e for e in finals if e["position"] == 3)
        assert wb_final is not None
        assert consolation_final is not None

    def test_round_numbers_assigned_by_week_order(self):
        from handler import _build_espn_brackets

        matchups = [
            {
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": 1,
                "loser": 2,
                "week": "15",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            }
        ]
        result = _build_espn_brackets(matchups)
        assert result[0]["round"] == 1

    def test_team_from_links_previous_round(self):
        from handler import _build_espn_brackets

        matchups = [
            {
                "team_a_id": 1,
                "team_b_id": 2,
                "winner": 1,
                "loser": 2,
                "week": "15",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
            {
                "team_a_id": 3,
                "team_b_id": 4,
                "winner": 3,
                "loser": 4,
                "week": "15",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
            {
                "team_a_id": 1,
                "team_b_id": 3,
                "winner": 1,
                "loser": 3,
                "week": "16",
                "season": "2024",
                "playoff_tier_type": "WINNERS_BRACKET",
            },
        ]
        result = _build_espn_brackets(matchups)
        final = next(e for e in result if e["round"] == 2)
        assert final["team_1_from"] is not None or final["team_2_from"] is not None
        if final["team_1_from"]:
            parsed = json.loads(final["team_1_from"])
            assert "w" in parsed or "l" in parsed


class TestRegisterEspnRawData:
    def test_processes_users_and_teams(self):
        from handler import _register_espn_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "users",
                "data": {
                    "members": [{"id": "user-1", "displayName": "Owner 1"}],
                    "teams": [{"id": 1, "name": "Team A", "primaryOwner": "user-1"}],
                },
            }
        ]
        result = _register_espn_raw_data(raw_data)
        assert len(result["members"]) == 1
        assert len(result["teams"]) == 1
        assert result["members"][0]["season"] == "2024"

    def test_extracts_league_name_from_settings(self):
        from handler import _register_espn_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "settings",
                "data": {"settings": {"name": "My ESPN League"}},
            }
        ]
        result = _register_espn_raw_data(raw_data)
        assert result["league_name_by_season"]["2024"] == "My ESPN League"

    def test_processes_draft_picks(self):
        from handler import _register_espn_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "draft_picks",
                "data": {
                    "draft_picks": [{"id": 1, "playerId": 123, "overallPickNumber": 1}]
                },
            }
        ]
        result = _register_espn_raw_data(raw_data)
        assert len(result["draft_picks"]) == 1
        assert result["draft_picks"][0]["season"] == "2024"

    def test_processes_player_scoring_totals(self):
        from handler import _register_espn_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "player_scoring_totals",
                "data": {
                    "player_scoring_totals": [
                        {
                            "player_id": 1,
                            "player_name": "QB One",
                            "position": 1,
                            "total_points": 300.5,
                        }
                    ]
                },
            }
        ]
        result = _register_espn_raw_data(raw_data)
        assert len(result["player_scoring_totals"]) == 1
        assert result["player_scoring_totals"][0]["position"] == "QB"

    def test_processes_matchups_with_tie(self):
        from handler import _register_espn_raw_data

        matchup = {
            "home": {
                "teamId": 1,
                "totalPoints": "100.0",
                "rosterForMatchupPeriod": {},
                "rosterForCurrentScoringPeriod": {},
            },
            "away": {
                "teamId": 2,
                "totalPoints": "100.0",
                "rosterForMatchupPeriod": {},
                "rosterForCurrentScoringPeriod": {},
            },
            "playoffTierType": "NONE",
            "matchupPeriodId": 1,
        }
        raw_data = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": {"matchups": [matchup]},
            }
        ]
        result = _register_espn_raw_data(raw_data)
        assert result["matchups"][0]["winner"] == "TIE"
        assert result["matchups"][0]["loser"] == "TIE"

    def test_processes_matchups_team_a_wins(self):
        from handler import _register_espn_raw_data

        matchup = {
            "home": {
                "teamId": 1,
                "totalPoints": "120.0",
                "rosterForMatchupPeriod": {},
                "rosterForCurrentScoringPeriod": {},
            },
            "away": {
                "teamId": 2,
                "totalPoints": "90.0",
                "rosterForMatchupPeriod": {},
                "rosterForCurrentScoringPeriod": {},
            },
            "playoffTierType": "NONE",
            "matchupPeriodId": 1,
        }
        raw_data = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": {"matchups": [matchup]},
            }
        ]
        result = _register_espn_raw_data(raw_data)
        assert result["matchups"][0]["winner"] == 1
        assert result["matchups"][0]["loser"] == 2

    def test_processes_matchups_team_b_wins(self):
        from handler import _register_espn_raw_data

        matchup = {
            "home": {
                "teamId": 1,
                "totalPoints": "80.0",
                "rosterForMatchupPeriod": {},
                "rosterForCurrentScoringPeriod": {},
            },
            "away": {
                "teamId": 2,
                "totalPoints": "110.0",
                "rosterForMatchupPeriod": {},
                "rosterForCurrentScoringPeriod": {},
            },
            "playoffTierType": "NONE",
            "matchupPeriodId": 1,
        }
        raw_data = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": {"matchups": [matchup]},
            }
        ]
        result = _register_espn_raw_data(raw_data)
        assert result["matchups"][0]["winner"] == 2
        assert result["matchups"][0]["loser"] == 1


class TestRegisterSleeperRawData:
    def test_processes_users_and_rosters(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "users",
                "data": [{"user_id": "u1", "display_name": "Owner 1"}],
            },
            {
                "season": "2024",
                "data_type": "rosters",
                "data": [{"roster_id": 1, "owner_id": "u1"}],
            },
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert len(result["users"]) == 1
        assert len(result["rosters"]) == 1

    def test_processes_league_settings_with_name(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "league_settings",
                "data": {
                    "name": "My Sleeper League",
                    "scoring_settings": {"pass_yd": 0.04},
                },
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert result["league_name_by_season"]["2024"] == "My Sleeper League"

    def test_processes_draft_picks(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "draft_picks",
                "data": [{"player_id": "player-1", "round": 1, "pick_no": 1}],
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert len(result["draft_picks"]) == 1

    def test_processes_playoff_bracket(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [{"t1": 1, "t2": 2, "m": 1, "r": 1, "w": 1, "l": 2, "p": 1}],
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert len(result["brackets"]) == 1
        assert result["brackets"][0]["bracket_type"] == "WINNERS_BRACKET"

    def test_processes_losers_bracket(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "losers_bracket",
                "data": [{"t1": 3, "t2": 4, "m": 2, "r": 1, "w": 3, "l": 4, "p": None}],
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert len(result["brackets"]) == 1
        assert result["brackets"][0]["bracket_type"] == "LOSERS_BRACKET"

    def test_skips_bye_bracket_entries(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [{"t1": None, "t2": 2, "m": 1, "r": 1}],
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert len(result["brackets"]) == 0

    def test_regular_season_matchup_has_none_tier(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": [
                    {
                        "matchup_id": 1,
                        "roster_id": 1,
                        "points": 100.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                    {
                        "matchup_id": 1,
                        "roster_id": 2,
                        "points": 90.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                ],
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert result["matchups"][0]["playoff_tier_type"] == "NONE"

    def test_playoff_matchup_tier_from_bracket(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "playoff_bracket",
                "data": [{"t1": 1, "t2": 2, "m": 1, "r": 1, "w": 1, "l": 2, "p": 1}],
            },
            {
                "season": "2024",
                "data_type": "matchups_week15",
                "data": [
                    {
                        "matchup_id": 1,
                        "roster_id": 1,
                        "points": 120.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                    {
                        "matchup_id": 1,
                        "roster_id": 2,
                        "points": 90.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                ],
            },
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert result["matchups"][0]["playoff_tier_type"] == "WINNERS_BRACKET"

    def test_processes_matchups_team_b_wins(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": [
                    {
                        "matchup_id": 1,
                        "roster_id": 1,
                        "points": 80.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                    {
                        "matchup_id": 1,
                        "roster_id": 2,
                        "points": 120.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                ],
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert result["matchups"][0]["winner"] == 2
        assert result["matchups"][0]["loser"] == 1

    def test_tie_matchup_has_tie_winner_and_loser(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": [
                    {
                        "matchup_id": 1,
                        "roster_id": 1,
                        "points": 100.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                    {
                        "matchup_id": 1,
                        "roster_id": 2,
                        "points": 100.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                ],
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert result["matchups"][0]["winner"] == "TIE"
        assert result["matchups"][0]["loser"] == "TIE"

    def test_skips_unpaired_matchup(self):
        from handler import _register_sleeper_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "matchups_week1",
                "data": [
                    {
                        "matchup_id": 1,
                        "roster_id": 1,
                        "points": 100.0,
                        "starters": [],
                        "starters_points": [],
                        "players": [],
                        "players_points": {},
                    },
                ],
            }
        ]
        result = _register_sleeper_raw_data(raw_data, player_metadata={})
        assert len(result["matchups"]) == 0


class TestRegisterRawData:
    def test_espn_platform_registers_views(self):
        from handler import register_raw_data

        raw_data = [
            {
                "season": "2024",
                "data_type": "users",
                "data": {"members": [], "teams": []},
            }
        ]
        con = MagicMock()
        result = register_raw_data(raw_data=raw_data, con=con, platform="ESPN")
        assert "members" in result
        assert "teams" in result

    def test_sleeper_platform_registers_views(self):
        from handler import register_raw_data

        raw_data = [
            {"season": "2024", "data_type": "users", "data": []},
        ]
        con = MagicMock()
        result = register_raw_data(
            raw_data=raw_data, con=con, platform="SLEEPER", player_metadata={}
        )
        assert "users" in result

    def test_unsupported_platform_raises_value_error(self):
        from handler import register_raw_data

        con = MagicMock()
        with pytest.raises(ValueError, match="Unsupported platform"):
            register_raw_data(raw_data=[], con=con, platform="YAHOO")


class TestWriteItems:
    def test_calls_batch_writer_put_item(self, mock_table):
        from handler import write_items

        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.name = "test-table"

        items = [{"PK": "LEAGUE#abc", "SK": "TEAMS#2024", "data": []}]
        write_items(items)

        mock_writer.put_item.assert_called_once_with(Item=items[0])

    def test_handles_empty_items_list(self, mock_table):
        from handler import write_items

        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.name = "test-table"

        write_items([])
        mock_writer.put_item.assert_not_called()


class TestLambdaHandler:
    def _make_event(
        self,
        principal="user:role",
        bucket="my-bucket",
        key="raw-api-data/canon-123/manifest.json",
    ):
        return {
            "Records": [
                {
                    "userIdentity": {"principalId": principal},
                    "s3": {
                        "bucket": {"name": bucket},
                        "object": {"key": key},
                    },
                }
            ]
        }

    def test_raises_on_malformed_event(self):
        from handler import lambda_handler

        with pytest.raises(ValueError, match="Unexpected S3 event structure"):
            lambda_handler({"Records": [{}]}, MagicMock())

    def test_skips_replication_event(self, mock_s3_client):
        from handler import lambda_handler

        event = self._make_event(principal="s3-replication")
        with patch("handler.read_s3_object") as mock_read:
            lambda_handler(event, MagicMock())

        mock_read.assert_not_called()

    def test_espn_full_flow(self, mock_s3_client, mock_table, mock_ddb_client):
        from handler import lambda_handler

        event = self._make_event()

        def mock_read(bucket, key, version_id=None):
            if "manifest" in key:
                return {"ESPN": ["2024"]}
            return []

        mock_s3_client.list_object_versions.return_value = {"Versions": []}

        grouped = {
            "members": [],
            "teams": [],
            "matchups": [],
            "brackets": [],
            "draft_picks": [],
            "player_scoring_totals": [],
            "league_name_by_season": {"2024": "Test League"},
        }

        mock_con = MagicMock()
        mock_rel = MagicMock()
        mock_rel.fetchall.return_value = []
        mock_rel.description = []
        mock_con.sql.return_value = mock_rel

        with (
            patch("handler.read_s3_object", side_effect=mock_read),
            patch("handler.register_raw_data", return_value=grouped),
            patch("handler.dataframe_to_dynamo_items", return_value=[]),
            patch("handler.write_items"),
            patch("handler.write_metadata_items"),
            patch("handler.duckdb") as mock_duckdb,
        ):
            mock_duckdb.connect.return_value = mock_con
            lambda_handler(event, MagicMock())

    def test_sleeper_loads_player_metadata_and_stats(
        self, mock_s3_client, mock_table, mock_ddb_client
    ):
        from handler import lambda_handler

        event = self._make_event()

        def mock_read(bucket, key, version_id=None):
            if "manifest" in key:
                return {"SLEEPER": ["2024"]}
            elif "sleeper_nfl_players" in key:
                return {"player-1": {"first_name": "Pat", "last_name": "M"}}
            elif "sleeper_nfl_player_stats" in key:
                return {"player-1": {"2024": {"pass_yd": 4000}}}
            return []

        mock_s3_client.list_object_versions.return_value = {"Versions": []}

        grouped = {
            "users": [],
            "rosters": [],
            "matchups": [],
            "brackets": [],
            "draft_picks": [],
            "player_scoring_totals": [],
            "league_name_by_season": {},
        }

        mock_con = MagicMock()
        mock_rel = MagicMock()
        mock_rel.fetchall.return_value = []
        mock_rel.description = []
        mock_con.sql.return_value = mock_rel

        with (
            patch("handler.read_s3_object", side_effect=mock_read),
            patch("handler.register_raw_data", return_value=grouped),
            patch("handler.dataframe_to_dynamo_items", return_value=[]),
            patch("handler.write_items"),
            patch("handler.write_metadata_items"),
            patch("handler.duckdb") as mock_duckdb,
        ):
            mock_duckdb.connect.return_value = mock_con
            lambda_handler(event, MagicMock())

    def test_sleeper_gracefully_handles_missing_player_metadata(
        self, mock_s3_client, mock_table, mock_ddb_client
    ):
        import botocore.exceptions
        from handler import lambda_handler

        event = self._make_event()

        no_such_key_error = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "GetObject"
        )

        def mock_read(bucket, key, version_id=None):
            if "manifest" in key:
                return {"SLEEPER": ["2024"]}
            elif "sleeper_nfl_players" in key:
                raise no_such_key_error
            elif "sleeper_nfl_player_stats" in key:
                raise no_such_key_error
            return []

        mock_s3_client.list_object_versions.return_value = {"Versions": []}

        grouped = {
            "users": [],
            "rosters": [],
            "matchups": [],
            "brackets": [],
            "draft_picks": [],
            "player_scoring_totals": [],
            "league_name_by_season": {},
        }

        mock_con = MagicMock()
        mock_rel = MagicMock()
        mock_rel.fetchall.return_value = []
        mock_rel.description = []
        mock_con.sql.return_value = mock_rel

        with (
            patch("handler.read_s3_object", side_effect=mock_read),
            patch("handler.register_raw_data", return_value=grouped),
            patch("handler.dataframe_to_dynamo_items", return_value=[]),
            patch("handler.write_items"),
            patch("handler.write_metadata_items"),
            patch("handler.duckdb") as mock_duckdb,
        ):
            mock_duckdb.connect.return_value = mock_con
            lambda_handler(event, MagicMock())

    def test_raises_when_player_metadata_load_fails_non_nosuchkey(
        self, mock_s3_client, mock_table, mock_ddb_client
    ):
        from handler import lambda_handler

        event = self._make_event()
        access_denied = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "GetObject"
        )

        def mock_read(bucket, key, version_id=None):
            if "manifest" in key:
                return {"SLEEPER": ["2024"]}
            elif "sleeper_nfl_players" in key:
                raise access_denied
            return []

        mock_s3_client.list_object_versions.return_value = {"Versions": []}

        with (
            patch("handler.read_s3_object", side_effect=mock_read),
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                lambda_handler(event, MagicMock())

    def test_raises_when_player_stats_load_fails_non_nosuchkey(
        self, mock_s3_client, mock_table, mock_ddb_client
    ):
        from handler import lambda_handler

        event = self._make_event()
        access_denied = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "GetObject"
        )

        def mock_read(bucket, key, version_id=None):
            if "manifest" in key:
                return {"SLEEPER": ["2024"]}
            elif "sleeper_nfl_players" in key:
                return {"player-1": {"first_name": "Pat"}}
            elif "sleeper_nfl_player_stats" in key:
                raise access_denied
            return []

        mock_s3_client.list_object_versions.return_value = {"Versions": []}

        with (
            patch("handler.read_s3_object", side_effect=mock_read),
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                lambda_handler(event, MagicMock())

    def test_raises_when_season_load_fails(
        self, mock_s3_client, mock_table, mock_ddb_client
    ):
        import botocore.exceptions
        from handler import lambda_handler

        event = self._make_event()

        def mock_read(bucket, key, version_id=None):
            if "manifest" in key:
                return {"ESPN": ["2024"]}
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "GetObject"
            )

        mock_s3_client.list_object_versions.return_value = {"Versions": []}

        with (
            patch("handler.read_s3_object", side_effect=mock_read),
        ):
            with pytest.raises(RuntimeError, match="Failed to load seasons"):
                lambda_handler(event, MagicMock())

    def test_previous_manifest_used_when_version_exists(
        self, mock_s3_client, mock_table, mock_ddb_client
    ):
        from handler import lambda_handler

        event = self._make_event()

        call_keys = []

        def mock_read(bucket, key, version_id=None):
            call_keys.append((key, version_id))
            if "manifest" in key and version_id is None:
                return {"ESPN": ["2023", "2024"]}
            elif "manifest" in key and version_id == "prev-v1":
                return {"ESPN": ["2023"]}
            return []

        mock_s3_client.list_object_versions.return_value = {
            "Versions": [
                {
                    "Key": "raw-api-data/canon-123/manifest.json",
                    "VersionId": "v2",
                    "LastModified": __import__("datetime").datetime(
                        2024, 2, 1, tzinfo=__import__("datetime").timezone.utc
                    ),
                },
                {
                    "Key": "raw-api-data/canon-123/manifest.json",
                    "VersionId": "prev-v1",
                    "LastModified": __import__("datetime").datetime(
                        2024, 1, 1, tzinfo=__import__("datetime").timezone.utc
                    ),
                },
            ]
        }

        grouped = {
            "members": [],
            "teams": [],
            "matchups": [],
            "brackets": [],
            "draft_picks": [],
            "player_scoring_totals": [],
            "league_name_by_season": {},
        }

        mock_con = MagicMock()
        mock_rel = MagicMock()
        mock_rel.fetchall.return_value = []
        mock_rel.description = []
        mock_con.sql.return_value = mock_rel

        with (
            patch("handler.read_s3_object", side_effect=mock_read),
            patch("handler.register_raw_data", return_value=grouped),
            patch("handler.dataframe_to_dynamo_items", return_value=[]),
            patch("handler.write_items"),
            patch("handler.write_metadata_items"),
            patch("handler.duckdb") as mock_duckdb,
        ):
            mock_duckdb.connect.return_value = mock_con
            lambda_handler(event, MagicMock())

        prev_manifest_read = [k for k in call_keys if k[1] == "prev-v1"]
        assert len(prev_manifest_read) == 1


class TestReadS3Object:
    def test_reads_and_parses_json(self, mock_s3_client):
        from handler import read_s3_object

        mock_s3_client.get_object.return_value = {
            "Body": type(
                "Body",
                (),
                {"read": lambda self: b'{"key": "value"}'},
            )()
        }
        result = read_s3_object("my-bucket", "my-key")
        assert result == {"key": "value"}

    def test_passes_version_id_when_provided(self, mock_s3_client):
        from handler import read_s3_object

        mock_s3_client.get_object.return_value = {
            "Body": type(
                "Body",
                (),
                {"read": lambda self: b'{"v": "2"}'},
            )()
        }
        read_s3_object("bucket", "key", version_id="abc123")
        call_kwargs = mock_s3_client.get_object.call_args[1]
        assert call_kwargs.get("VersionId") == "abc123"

    def test_raises_on_client_error(self, mock_s3_client):
        from handler import read_s3_object

        mock_s3_client.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
        )
        with pytest.raises(botocore.exceptions.ClientError):
            read_s3_object("bucket", "missing-key")


class TestGetPreviousVersionId:
    def test_returns_second_most_recent_version(self, mock_s3_client):
        from handler import get_previous_version_id
        from datetime import datetime, timezone

        mock_s3_client.list_object_versions.return_value = {
            "Versions": [
                {
                    "Key": "my/key",
                    "VersionId": "v2",
                    "LastModified": datetime(2024, 2, 1, tzinfo=timezone.utc),
                },
                {
                    "Key": "my/key",
                    "VersionId": "v1",
                    "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc),
                },
            ]
        }
        result = get_previous_version_id("bucket", "my/key")
        assert result == "v1"

    def test_returns_none_when_single_version(self, mock_s3_client):
        from handler import get_previous_version_id
        from datetime import datetime, timezone

        mock_s3_client.list_object_versions.return_value = {
            "Versions": [
                {
                    "Key": "my/key",
                    "VersionId": "v1",
                    "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc),
                }
            ]
        }
        result = get_previous_version_id("bucket", "my/key")
        assert result is None

    def test_filters_versions_by_key(self, mock_s3_client):
        from handler import get_previous_version_id
        from datetime import datetime, timezone

        mock_s3_client.list_object_versions.return_value = {
            "Versions": [
                {
                    "Key": "other/key",
                    "VersionId": "v99",
                    "LastModified": datetime(2024, 3, 1, tzinfo=timezone.utc),
                },
                {
                    "Key": "my/key",
                    "VersionId": "v1",
                    "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc),
                },
            ]
        }
        result = get_previous_version_id("bucket", "my/key")
        assert result is None


class TestDataframeToDynamoItems:
    def test_groups_rows_by_sort_key(self):
        from handler import dataframe_to_dynamo_items, EntityType, KeySchema

        con = duckdb.connect()
        df = pd.DataFrame(
            [
                {"season": "2024", "team_id": "1", "wins": 10},
                {"season": "2024", "team_id": "2", "wins": 8},
                {"season": "2023", "team_id": "1", "wins": 6},
            ]
        )
        con.register("test_data", df)
        rel = con.sql("SELECT * FROM test_data")

        schema = KeySchema(
            pk="LEAGUE#abc",
            sk=lambda row: f"TEAMS#{row['season']}",
            entity_type=EntityType.TEAMS,
        )
        items = dataframe_to_dynamo_items(rel, schema)
        assert len(items) == 2
        sks = {item["SK"] for item in items}
        assert "TEAMS#2024" in sks
        assert "TEAMS#2023" in sks
        item_2024 = next(i for i in items if i["SK"] == "TEAMS#2024")
        assert len(item_2024["data"]) == 2

    def test_sanitizes_float_values(self):
        from handler import dataframe_to_dynamo_items, EntityType, KeySchema

        con = duckdb.connect()
        df = pd.DataFrame([{"season": "2024", "score": 105.5}])
        con.register("test_data", df)
        rel = con.sql("SELECT * FROM test_data")

        schema = KeySchema(
            pk="LEAGUE#abc",
            sk=lambda row: f"TEAMS#{row['season']}",
            entity_type=EntityType.TEAMS,
        )
        items = dataframe_to_dynamo_items(rel, schema)
        assert items[0]["data"][0]["score"] == Decimal("105.5")


class TestWriteMetadataItems:
    def test_sets_onboarding_status_completed(self, mock_ddb_client, mock_table):
        from handler import write_metadata_items

        mock_table.name = "test-table"
        write_metadata_items(league_id="abc123", refresh=False)
        call_args = mock_ddb_client.transact_write_items.call_args[1]
        update = call_args["TransactItems"][0]["Update"]
        assert update["ExpressionAttributeValues"][":val"] == {"S": "COMPLETED"}
        assert "onboarding_status" in update["UpdateExpression"]

    def test_sets_refresh_status_completed(self, mock_ddb_client, mock_table):
        from handler import write_metadata_items

        mock_table.name = "test-table"
        write_metadata_items(league_id="abc123", refresh=True)
        call_args = mock_ddb_client.transact_write_items.call_args[1]
        update = call_args["TransactItems"][0]["Update"]
        assert "refresh_status" in update["UpdateExpression"]

    def test_includes_league_name_when_provided(self, mock_ddb_client, mock_table):
        from handler import write_metadata_items

        mock_table.name = "test-table"
        write_metadata_items(league_id="abc123", refresh=False, league_name="My League")
        call_args = mock_ddb_client.transact_write_items.call_args[1]
        update = call_args["TransactItems"][0]["Update"]
        assert "league_name" in update["UpdateExpression"]
        assert update["ExpressionAttributeValues"][":league_name"] == {"S": "My League"}
