"""Tests for Yahoo processing: _register_yahoo_raw_data + YAHOO query transforms."""

from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest


def _raw_data():
    return [
        {
            "season": "2025",
            "data_type": "settings",
            "data": {
                "name": "My League",
                "num_playoff_teams": "6",
                "playoff_start_week": "15",
            },
        },
        {
            "season": "2025",
            "data_type": "standings",
            "data": {
                "standings": [
                    {"team_key": "461.l.100.t.1", "rank": "1"},
                    {"team_key": "461.l.100.t.2", "rank": "2"},
                ]
            },
        },
        {
            "season": "2025",
            "data_type": "teams",
            "data": {
                "members": [
                    {"manager_id": "G1", "nickname": "Alice"},
                    {"manager_id": "G2", "nickname": "Bob"},
                ],
                "teams": [
                    {
                        "team_key": "461.l.100.t.1",
                        "team_id": "1",
                        "name": "Team A",
                        "logo": "logoA",
                        "manager_id": "G1",
                    },
                    {
                        "team_key": "461.l.100.t.2",
                        "team_id": "2",
                        "name": "Team B",
                        "logo": "logoB",
                        "manager_id": "G2",
                    },
                ],
            },
        },
        {
            "season": "2025",
            "data_type": "matchups_week1",
            "data": {
                "matchups": [
                    {
                        "week": "1",
                        "is_playoffs": "0",
                        "is_consolation": "0",
                        "winner_team_key": "461.l.100.t.1",
                        "teams": [
                            {"team_key": "461.l.100.t.1", "points": "100.5"},
                            {"team_key": "461.l.100.t.2", "points": "90.0"},
                        ],
                    }
                ]
            },
        },
        {
            "season": "2025",
            "data_type": "rosters_week1",
            "data": {
                "rosters": [
                    {
                        "team_key": "461.l.100.t.1",
                        "week": "1",
                        "player_key": "461.p.1",
                        "player_name": "QB One",
                        "position": "QB",
                        "selected_position": "QB",
                        "points": "22.5",
                    },
                    {
                        "team_key": "461.l.100.t.1",
                        "week": "1",
                        "player_key": "461.p.9",
                        "player_name": "Bench Guy",
                        "position": "RB",
                        "selected_position": "BN",
                        "points": "1.0",
                    },
                ]
            },
        },
        {
            "season": "2025",
            "data_type": "draft_picks",
            "data": {
                "draft_picks": [
                    {
                        "pick": "1",
                        "round": "1",
                        "team_key": "461.l.100.t.1",
                        "player_key": "461.p.1",
                        "cost": None,
                    },
                    {
                        "pick": "2",
                        "round": "1",
                        "team_key": "461.l.100.t.2",
                        "player_key": "461.p.2",
                        "cost": None,
                    },
                ]
            },
        },
        {
            "season": "2025",
            "data_type": "transactions",
            "data": {
                "transactions": [
                    {
                        "transaction_key": "461.l.100.tr.1",
                        "type": "add/drop",
                        "timestamp": "1700000000",
                        "faab_bid": "5",
                        "items": [
                            {
                                "player_key": "461.p.3",
                                "type": "add",
                                "destination_team_key": "461.l.100.t.1",
                                "source_team_key": None,
                            },
                            {
                                "player_key": "461.p.1",
                                "type": "drop",
                                "source_team_key": "461.l.100.t.1",
                                "destination_team_key": None,
                            },
                        ],
                    }
                ]
            },
        },
    ]


_METADATA = {
    "461.p.1": {"name": "QB One", "position": "QB"},
    "461.p.2": {"name": "RB Two", "position": "RB"},
    "461.p.3": {"name": "WR Three", "position": "WR"},
}
# Yahoo returns points as strings, so the stats cache stores them as strings. Keep these
# as strings so the DRAFT transform's arithmetic (VORP) is exercised against a text-typed
# `player_scoring_totals` column, which must be coerced to numeric before it binds.
_STATS = {"461.p.1": {"2025": "300.0"}, "461.p.2": {"2025": "250.0"}}


class TestRegisterYahooRawData:
    def test_grouped_shapes(self, processor_handler):
        grouped = processor_handler._register_yahoo_raw_data(
            _raw_data(), _METADATA, _STATS
        )
        # members deduped, ESPN-shaped
        assert {m["id"] for m in grouped["members"]} == {"G1", "G2"}
        team_a = next(t for t in grouped["teams"] if t["id"] == "461.l.100.t.1")
        assert team_a["owners"] == ["G1"]
        assert team_a["primaryOwner"] == "G1"
        assert team_a["rankCalculatedFinal"] == 1
        # matchup with starter/bench lineups joined from rosters
        m = grouped["matchups"][0]
        assert m["team_a_id"] == "461.l.100.t.1"
        assert m["team_a_score"] == 100.5
        assert m["winner"] == "461.l.100.t.1"
        assert m["playoff_tier_type"] == "NONE"
        assert [s["full_name"] for s in m["team_a_starters"]] == ["QB One"]
        assert [b["full_name"] for b in m["team_a_bench"]] == ["Bench Guy"]
        # player scoring from the cache
        assert {r["player_id"] for r in grouped["player_scoring_totals"]} == {
            "461.p.1",
            "461.p.2",
        }
        # transaction resolved + typed as waiver (faab present)
        txn = grouped["transactions"][0]
        assert txn["type"] == "waiver"
        assert txn["waiver_bid"] == "5"
        assert [a["player_name"] for a in txn["adds"]] == ["WR Three"]
        assert [d["player_name"] for d in txn["drops"]] == ["QB One"]
        # league settings + name
        settings = grouped["league_settings_by_season"]["2025"]
        assert settings["num_playoff_teams"] == 6
        assert settings["playoff_week_start"] == 15
        assert settings["regular_season_weeks"] == 14
        assert grouped["league_name_by_season"]["2025"] == "My League"

    def test_bye_matchup_skipped(self, processor_handler):
        raw = [
            {
                "season": "2025",
                "data_type": "matchups_week1",
                "data": {
                    "matchups": [
                        {"week": "1", "teams": [{"team_key": "t1", "points": "50"}]}
                    ]
                },
            }
        ]
        grouped = processor_handler._register_yahoo_raw_data(raw, {}, {})
        assert grouped["matchups"] == []


class TestYahooQueriesBind:
    def test_teams_matchups_draft_bind(self, processor_handler):
        """The YAHOO TEAMS/DRAFT SQL and the reused ESPN MATCHUPS SQL bind against Yahoo rows."""
        grouped = processor_handler._register_yahoo_raw_data(
            _raw_data(), _METADATA, _STATS
        )
        con = duckdb.connect()
        for view in (
            "members",
            "teams",
            "matchups",
            "draft_picks",
            "player_scoring_totals",
        ):
            con.register(view, pd.DataFrame(grouped[view]))

        teams_df = con.sql(processor_handler.QUERIES["TEAMS"]["YAHOO"]).df()
        con.register("teams_output", teams_df)
        assert set(teams_df["team_id"]) == {"461.l.100.t.1", "461.l.100.t.2"}
        assert teams_df.set_index("team_id").loc["461.l.100.t.1", "final_rank"] == 1

        matchups_df = con.sql(processor_handler.QUERIES["MATCHUPS"]["YAHOO"]).df()
        con.register("matchups_output", matchups_df)
        assert matchups_df.iloc[0]["team_a_score"] == 100.5

        draft_df = con.sql(processor_handler.QUERIES["DRAFT"]["YAHOO"]).df()
        rows = {r["player_id"]: r for r in draft_df.to_dict("records")}
        assert rows["461.p.1"]["overall_pick_number"] == 1
        assert rows["461.p.1"]["player_name"] == "QB One"
        # QB One scored 300 season points -> ranked #1 QB.
        assert rows["461.p.1"]["actual_position_rank"] == 1
        # total_points is coerced to numeric so VORP arithmetic binds (regression:
        # string-typed Yahoo points previously crashed the DRAFT transform with
        # `-(VARCHAR, VARCHAR)`).
        assert rows["461.p.1"]["total_points"] == 300.0
        con.close()

    def test_teams_survive_missing_manager(self, processor_handler):
        """A Yahoo team with no matching member row still appears (LEFT JOIN members).

        Regression: Yahoo may expose no manager for a team (private profiles), or the
        managers sub-collection may parse to null owner ids. An INNER JOIN dropped every
        such team, emptying teams_output and (via downstream INNER JOINs) every dependent
        view. The YAHOO TEAMS query LEFT JOINs so the team survives with a null owner.
        """
        con = duckdb.connect()
        # No members at all -> every team's primaryOwner has no match.
        con.register(
            "members", pd.DataFrame([], columns=["id", "displayName", "season"])
        )
        con.register(
            "teams",
            pd.DataFrame(
                [
                    {
                        "id": "461.l.100.t.1",
                        "name": "Orphan Team",
                        "logo": None,
                        "season": "2024",
                        "owners": [None],
                        "primaryOwner": None,
                        "rankCalculatedFinal": 1,
                    }
                ]
            ),
        )
        teams_df = con.sql(processor_handler.QUERIES["TEAMS"]["YAHOO"]).df()
        assert set(teams_df["team_id"]) == {"461.l.100.t.1"}
        assert teams_df.iloc[0]["team_name"] == "Orphan Team"
        assert pd.isna(teams_df.iloc[0]["display_name"])
        con.close()

    def test_standings_binds(self, processor_handler):
        grouped = processor_handler._register_yahoo_raw_data(
            _raw_data(), _METADATA, _STATS
        )
        con = duckdb.connect()
        for view in ("members", "teams", "matchups"):
            con.register(view, pd.DataFrame(grouped[view]))
        teams_df = con.sql(processor_handler.QUERIES["TEAMS"]["YAHOO"]).df()
        con.register("teams_output", teams_df)
        matchups_df = con.sql(processor_handler.QUERIES["MATCHUPS"]["YAHOO"]).df()
        con.register("matchups_output", matchups_df)
        standings_df = con.sql(processor_handler.QUERIES["STANDINGS"]).df()
        # Week-1 win for team 1 counts in standings.
        assert standings_df.set_index("team_id").loc["461.l.100.t.1", "wins"] == 1
        con.close()


def _playoff_game(week, a, b, winner, consolation=False):
    return {
        "season": "2025",
        "week": str(week),
        "is_playoffs": "1",
        "is_consolation": "1" if consolation else "0",
        "winner_team_key": winner,
        "teams": [{"team_key": a, "points": "100"}, {"team_key": b, "points": "90"}],
    }


# A 6-team bracket shaped like the reported league: t12/t4 bye in week 15; week 16 has a
# 5th-place game (t1 v t3); week 17 has the final (t10 v t12), a 3rd-place game (t4 v t5)
# and consolation-bracket games between teams that missed the playoffs.
_BRACKET_GAMES = [
    _playoff_game(15, "t1", "t10", "t10"),
    _playoff_game(15, "t3", "t5", "t5"),
    _playoff_game(15, "t2", "t8", "t2", consolation=True),
    _playoff_game(16, "t1", "t3", "t1"),
    _playoff_game(16, "t4", "t10", "t10"),
    _playoff_game(16, "t5", "t12", "t12"),
    _playoff_game(16, "t6", "t8", "t8", consolation=True),
    _playoff_game(17, "t4", "t5", "t4"),
    _playoff_game(17, "t10", "t12", "t12"),
    _playoff_game(17, "t2", "t9", "t2", consolation=True),
]


class TestClassifyYahooPlayoffTiers:
    def test_bracket_path(self, processor_handler):
        tiers = processor_handler._classify_yahoo_playoff_tiers(_BRACKET_GAMES)
        by_game = {
            (int(g["week"]), g["teams"][0]["team_key"]): t
            for g, t in zip(_BRACKET_GAMES, tiers)
        }
        assert by_game[(15, "t1")] == "WINNERS_BRACKET"
        assert by_game[(15, "t3")] == "WINNERS_BRACKET"
        assert by_game[(16, "t1")] == "WINNERS_CONSOLATION_LADDER"  # 5th place
        assert by_game[(16, "t4")] == "WINNERS_BRACKET"
        assert by_game[(16, "t5")] == "WINNERS_BRACKET"
        assert by_game[(17, "t4")] == "WINNERS_CONSOLATION_LADDER"  # 3rd place
        assert by_game[(17, "t10")] == "WINNERS_BRACKET"  # final
        for key in ((15, "t2"), (16, "t6"), (17, "t2")):
            assert by_game[key] == "LOSERS_CONSOLATION_LADDER"

    def test_regular_season_is_none(self, processor_handler):
        game = {**_playoff_game(1, "t1", "t2", "t1"), "is_playoffs": "0"}
        assert processor_handler._classify_yahoo_playoff_tiers([game]) == ["NONE"]

    def test_undecided_game_eliminates_nobody(self, processor_handler):
        games = [
            _playoff_game(15, "t1", "t2", None),
            _playoff_game(16, "t1", "t2", "t1"),
        ]
        assert processor_handler._classify_yahoo_playoff_tiers(games) == [
            "WINNERS_BRACKET",
            "WINNERS_BRACKET",
        ]

    def test_seasons_tracked_independently(self, processor_handler):
        games = [
            _playoff_game(15, "t1", "t2", "t1"),
            {**_playoff_game(16, "t2", "t3", "t2"), "season": "2024"},
        ]
        assert processor_handler._classify_yahoo_playoff_tiers(games) == [
            "WINNERS_BRACKET",
            "WINNERS_BRACKET",
        ]


class TestYahooSingleChampion:
    def test_one_champion_and_one_title_game(self, processor_handler):
        """Regression: a final-week 3rd-place game was also crowned champion."""
        teams = sorted(
            {t["team_key"] for g in _BRACKET_GAMES for t in g["teams"]} | {"t7", "t11"}
        )
        regular = [
            {
                "week": "1",
                "is_playoffs": "0",
                "is_consolation": "0",
                "winner_team_key": a,
                "teams": [
                    {"team_key": a, "points": "100"},
                    {"team_key": b, "points": "90"},
                ],
            }
            for a, b in zip(teams[::2], teams[1::2])
        ]
        raw = [
            {
                "season": "2025",
                "data_type": "teams",
                "data": {
                    "members": [{"manager_id": k, "nickname": k} for k in teams],
                    "teams": [
                        {"team_key": k, "name": k, "manager_id": k} for k in teams
                    ],
                },
            },
            {
                "season": "2025",
                "data_type": "matchups_week1",
                "data": {"matchups": regular},
            },
            {
                "season": "2025",
                "data_type": "matchups_playoffs",
                "data": {"matchups": [dict(g) for g in _BRACKET_GAMES]},
            },
        ]
        grouped = processor_handler._register_yahoo_raw_data(raw, {}, {})
        finals = [b for b in grouped["brackets"] if b["position"] == 1]
        assert [(b["team_1"], b["team_2"], b["winner"]) for b in finals] == [
            ("t10", "t12", "t12")
        ]
        third = next(
            b for b in grouped["brackets"] if b["team_1"] == "t4" and b["round"] == 3
        )
        assert third["position"] == 3

        con = duckdb.connect()
        for view in ("members", "teams", "matchups"):
            con.register(view, pd.DataFrame(grouped[view]))
        con.register(
            "teams_output", con.sql(processor_handler.QUERIES["TEAMS"]["YAHOO"]).df()
        )
        con.register(
            "matchups_output",
            con.sql(processor_handler.QUERIES["MATCHUPS"]["YAHOO"]).df(),
        )
        standings = con.sql(processor_handler.QUERIES["STANDINGS"]).df()
        assert list(standings.loc[standings["champion"] == "Yes", "team_id"]) == ["t12"]
        con.close()


class TestStandingsChampion:
    @staticmethod
    def _standings(processor_handler, matchups):
        con = duckdb.connect()
        teams = sorted({m[k] for m in matchups for k in ("team_a_id", "team_b_id")})
        con.register(
            "teams_output",
            pd.DataFrame(
                [
                    {
                        "team_id": t,
                        "season": "2025",
                        "team_name": t,
                        "team_logo": None,
                        "display_name": t,
                        "final_rank": None,
                    }
                    for t in teams
                ]
            ),
        )
        rows = [
            {
                "season": "2025",
                "team_a_primary_owner_id": m["team_a_id"],
                "team_b_primary_owner_id": m["team_b_id"],
                "winner": m["team_a_id"],
                **m,
            }
            for m in matchups
        ]
        con.register("matchups_output", pd.DataFrame(rows))
        df = con.sql(processor_handler.QUERIES["STANDINGS"]).df()
        con.close()
        return sorted(df.loc[df["champion"] == "Yes", "team_id"])

    @staticmethod
    def _game(week, a, b, tier):
        return {
            "week": str(week),
            "team_a_id": a,
            "team_b_id": b,
            "team_a_score": 100.0,
            "team_b_score": 90.0,
            "playoff_tier_type": tier,
        }

    def test_title_game_before_week_17(self, processor_handler):
        """A league whose playoffs end in week 16 still gets its champion."""
        games = [
            self._game(1, "a", "b", "NONE"),
            self._game(1, "c", "d", "NONE"),
            self._game(15, "a", "b", "WINNERS_BRACKET"),
            self._game(15, "c", "d", "WINNERS_BRACKET"),
            self._game(16, "a", "c", "WINNERS_BRACKET"),
        ]
        assert self._standings(processor_handler, games) == ["a"]

    def test_mid_playoffs_names_no_champion(self, processor_handler):
        """The latest winners-bracket week is still the semifinals -> no champion yet."""
        games = [
            self._game(1, "a", "b", "NONE"),
            self._game(1, "c", "d", "NONE"),
            self._game(15, "a", "b", "WINNERS_BRACKET"),
            self._game(15, "c", "d", "WINNERS_BRACKET"),
        ]
        assert self._standings(processor_handler, games) == []


_TXN_TEAM_MAP = {
    "2025": {
        "t1": {"team_name": "Team 1", "display_name": "One"},
        "t2": {"team_name": "Team 2", "display_name": "Two"},
    }
}
_TXN_PLAYERS = {"p1": {"name": "Player 1", "position": "RB"}, "p2": {"name": "P2"}}
_TXN_CALENDAR = {"2025": [(1, "2025-09-08"), (2, "2025-09-15"), (3, "2025-09-22")]}


class TestCompileYahooTransactions:
    def test_trade_items_become_adds_and_drops(self, processor_handler):
        txn = {
            "transaction_key": "tr.1",
            "type": "trade",
            "timestamp": "1757700000",
            "faab_bid": None,
            "items": [
                {
                    "player_key": "p1",
                    "type": "trade",
                    "source_team_key": "t1",
                    "destination_team_key": "t2",
                },
                {
                    "player_key": "p2",
                    "type": "trade",
                    "source_team_key": "t2",
                    "destination_team_key": "t1",
                },
            ],
        }
        (row,) = processor_handler.compile_yahoo_transactions(
            [(txn, "2025")], _TXN_TEAM_MAP, _TXN_PLAYERS
        )
        assert row["type"] == "trade"
        assert [(a["player_id"], a["roster_id"]) for a in row["adds"]] == [
            ("p1", "t2"),
            ("p2", "t1"),
        ]
        assert [(d["player_id"], d["roster_id"]) for d in row["drops"]] == [
            ("p1", "t1"),
            ("p2", "t2"),
        ]
        assert row["roster_ids"] == ["t2", "t1"]
        assert [t["team_name"] for t in row["teams"]] == ["Team 2", "Team 1"]
        # No calendar -> week unresolved.
        assert row["week"] is None

    @pytest.mark.parametrize(
        ("timestamp", "expected_week"),
        [
            ("1756000000", 1),  # late Aug 2025: preseason clamps to week 1
            ("1757300000", 1),  # 2025-09-07 (Sun) in week 1
            # 2025-09-16 03:00 UTC = 2025-09-15 22:00 ET (Mon night) -> still week 2
            ("1757991600", 2),
            ("1758100000", 3),  # 2025-09-17 in week 3
            ("1790000000", 3),  # after the last week clamps to it
        ],
    )
    def test_week_and_created(self, processor_handler, timestamp, expected_week):
        txn = {
            "transaction_key": "tr.2",
            "type": "add",
            "timestamp": timestamp,
            "faab_bid": "4",
            "items": [
                {"player_key": "p1", "type": "add", "destination_team_key": "t1"}
            ],
        }
        (row,) = processor_handler.compile_yahoo_transactions(
            [(txn, "2025")], _TXN_TEAM_MAP, _TXN_PLAYERS, _TXN_CALENDAR
        )
        assert row["week"] == expected_week
        assert row["created"] == int(timestamp) * 1000
        assert row["type"] == "waiver"

    def test_missing_timestamp(self, processor_handler):
        txn = {"transaction_key": "tr.3", "type": "drop", "items": []}
        (row,) = processor_handler.compile_yahoo_transactions(
            [(txn, "2025")], _TXN_TEAM_MAP, _TXN_PLAYERS, _TXN_CALENDAR
        )
        assert row["created"] is None
        assert row["week"] is None

    def test_calendar_from_raw_game_weeks(self, processor_handler):
        raw = _raw_data() + [
            {
                "season": "2025",
                "data_type": "game_weeks",
                "data": {
                    "game_weeks": [
                        {"week": "2", "start": "2023-11-14", "end": "2023-11-20"},
                        {"week": "1", "start": "2023-11-07", "end": "2023-11-13"},
                        {"week": None, "start": "x", "end": "y"},
                    ]
                },
            }
        ]
        grouped = processor_handler._register_yahoo_raw_data(raw, _METADATA, _STATS)
        # 1700000000 = 2023-11-14 22:13 UTC -> 17:13 ET on Nov 14 -> week 2.
        assert grouped["transactions"][0]["week"] == 2
        assert grouped["transactions"][0]["created"] == 1700000000000


def _store_row(team_key, player_key, slot, points):
    return {
        "team_key": team_key,
        "week": "1",
        "player_key": player_key,
        "player_name": player_key,
        "position": "WR",
        "selected_position": slot,
        "points": points,
    }


_STORE = {
    "weeks": {
        "1": [
            _store_row("461.l.100.t.1", "461.p.1", "QB", "60.5"),
            _store_row("461.l.100.t.1", "461.p.4", "WR", "40.0"),
            _store_row("461.l.100.t.1", "461.p.5", "BN", "7.0"),
            _store_row("461.l.100.t.2", "461.p.2", "RB", "90.0"),
        ]
    }
}


def _without_rosters():
    return [r for r in _raw_data() if not r["data_type"].startswith("rosters")]


class TestMergeYahooLineupStores:
    """backend/data-processing-pipeline: backfilled lineups are merged into matchups."""

    @staticmethod
    def _matchup(processor_handler, raw):
        grouped = processor_handler._register_yahoo_raw_data(raw, _METADATA, _STATS)
        return grouped["matchups"][0]

    def test_store_lineups_attached_and_starters_sum_to_score(self, processor_handler):
        raw = processor_handler.merge_yahoo_lineup_stores(
            _without_rosters(), {"2025": _STORE}
        )
        m = self._matchup(processor_handler, raw)
        a_starters = sum(p["points_scored"] for p in m["team_a_starters"])
        b_starters = sum(p["points_scored"] for p in m["team_b_starters"])
        assert a_starters == m["team_a_score"] == 100.5
        assert b_starters == m["team_b_score"] == 90.0
        assert [p["player_id"] for p in m["team_a_bench"]] == ["461.p.5"]

    def test_store_overrides_in_file_rosters_for_the_same_week(self, processor_handler):
        raw = processor_handler.merge_yahoo_lineup_stores(_raw_data(), {"2025": _STORE})
        assert [r["data_type"] for r in raw].count("rosters_week1") == 1
        m = self._matchup(processor_handler, raw)
        assert "Bench Guy" not in [p["full_name"] for p in m["team_a_bench"]]

    def test_legacy_in_file_rosters_used_without_store(self, processor_handler):
        raw = processor_handler.merge_yahoo_lineup_stores(_raw_data(), {"2025": None})
        m = self._matchup(processor_handler, raw)
        assert [s["full_name"] for s in m["team_a_starters"]] == ["QB One"]

    def test_store_keeps_in_file_weeks_it_does_not_cover(self, processor_handler):
        store = {"weeks": {"2": []}}
        raw = processor_handler.merge_yahoo_lineup_stores(_raw_data(), {"2025": store})
        assert [
            r["data_type"] for r in raw if r["data_type"].startswith("rosters")
        ] == [
            "rosters_week1",
            "rosters_week2",
        ]

    def test_no_lineups_yields_empty_lineups(self, processor_handler):
        raw = processor_handler.merge_yahoo_lineup_stores(
            _without_rosters(), {"2025": None}
        )
        m = self._matchup(processor_handler, raw)
        assert m["team_a_starters"] == m["team_a_bench"] == []
        assert m["team_a_score"] == 100.5


# ── Cross-season owner identities (backend/data-processing-pipeline) ─────────────────────

_DEFAULT_LOGO = "https://s.yimg.com/cv/apiv2/default/nfl/nfl_5.png"


def _season_teams(season, teams):
    """A raw Yahoo ``teams`` record. ``teams`` is a list of dicts with ``slot`` and optional
    ``nickname``/``name``/``logo``/``guid``; rows carry the post-change ``guid``/``slot`` fields."""
    game = {"2019": "390", "2020": "399", "2021": "406", "2022": "414"}[season]
    members, rows = [], []
    for t in teams:
        slot = str(t["slot"])
        guid = t.get("guid")
        owner = guid or slot
        members.append(
            {
                "manager_id": owner,
                "nickname": t.get("nickname"),
                "guid": guid,
                "slot_manager_id": slot,
            }
        )
        rows.append(
            {
                "team_key": f"{game}.l.1.t.{slot}",
                "team_id": slot,
                "name": t.get("name", f"Team {season}-{slot}"),
                "logo": t.get("logo", _DEFAULT_LOGO),
                "manager_id": owner,
                "guid": guid,
                "slot_manager_id": slot,
            }
        )
    return {"members": members, "teams": rows}


def _ids(owner_by_team, season, slot):
    game = {"2019": "390", "2020": "399", "2021": "406", "2022": "414"}[season]
    return owner_by_team[(season, f"{game}.l.1.t.{slot}")]


class TestResolveYahooOwnerIdentities:
    def test_slot_change_keeps_person_and_new_slot_holder_differs(
        self, processor_handler
    ):
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams("2019", [{"slot": 10, "nickname": "Manager A"}]),
                "2020": _season_teams(
                    "2020",
                    [
                        {"slot": 9, "nickname": "Manager A"},
                        {"slot": 10, "nickname": "Manager D"},
                    ],
                ),
            }
        )
        assert _ids(out, "2019", 10) == _ids(out, "2020", 9) == "390.l.1.t.10"
        assert _ids(out, "2020", 10) == "399.l.1.t.10"

    def test_returning_manager_after_gap(self, processor_handler):
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams("2019", [{"slot": 3, "nickname": "Manager A"}]),
                "2020": _season_teams("2020", [{"slot": 3, "nickname": "Manager B"}]),
                "2021": _season_teams(
                    "2021",
                    [
                        {"slot": 3, "nickname": "Manager B"},
                        {"slot": 8, "nickname": "Manager A"},
                    ],
                ),
            }
        )
        assert _ids(out, "2021", 8) == _ids(out, "2019", 3)
        assert _ids(out, "2021", 3) == _ids(out, "2020", 3) != _ids(out, "2019", 3)

    def test_guid_takes_precedence_and_is_the_id(self, processor_handler):
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams(
                    "2019", [{"slot": 1, "nickname": "Manager A", "guid": "GA"}]
                ),
                "2020": _season_teams(
                    "2020",
                    [
                        {"slot": 2, "nickname": "Renamed", "guid": "GA"},
                        # Same nickname, different guid: guid wins, so a new person.
                        {"slot": 1, "nickname": "Manager A", "guid": "GZ"},
                    ],
                ),
            }
        )
        assert _ids(out, "2019", 1) == _ids(out, "2020", 2) == "GA"
        assert _ids(out, "2020", 1) == "GZ"

    def test_hidden_nickname_never_merges(self, processor_handler):
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams("2019", [{"slot": 12, "nickname": "--hidden--"}]),
                "2020": _season_teams("2020", [{"slot": 12, "nickname": "--hidden--"}]),
            }
        )
        assert _ids(out, "2019", 12) != _ids(out, "2020", 12)

    def test_duplicate_nickname_in_season_never_merges(self, processor_handler):
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams("2019", [{"slot": 1, "nickname": "Manager A"}]),
                "2020": _season_teams(
                    "2020",
                    [
                        {"slot": 1, "nickname": "Manager A"},
                        {"slot": 2, "nickname": "manager a "},
                    ],
                ),
            }
        )
        ids_2020 = {_ids(out, "2020", 1), _ids(out, "2020", 2)}
        assert _ids(out, "2019", 1) not in ids_2020
        assert len(ids_2020) == 2

    def test_team_name_links_renamed_manager(self, processor_handler):
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams(
                    "2019", [{"slot": 4, "nickname": "Old Nick", "name": "Team X"}]
                ),
                "2020": _season_teams(
                    "2020", [{"slot": 6, "nickname": "New Nick", "name": "team x"}]
                ),
            }
        )
        assert _ids(out, "2019", 4) == _ids(out, "2020", 6)

    def test_custom_logo_links_renamed_manager(self, processor_handler):
        logo = "https://example.test/fantasy-logos/custom_1.jpg"
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams(
                    "2019", [{"slot": 4, "nickname": "Old", "name": "N1", "logo": logo}]
                ),
                "2020": _season_teams(
                    "2020", [{"slot": 6, "nickname": "New", "name": "N2", "logo": logo}]
                ),
            }
        )
        assert _ids(out, "2019", 4) == _ids(out, "2020", 6)

    @pytest.mark.parametrize(
        "logo",
        [
            "https://s.yimg.com/cv/apiv2/default/nfl/nfl_5.png",
            "https://s.yimg.com/cv/apiv2/nfl/nfl_10_d.png",
        ],
    )
    def test_default_logo_never_links(self, processor_handler, logo):
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams(
                    "2019", [{"slot": 4, "nickname": "P", "name": "N1", "logo": logo}]
                ),
                "2020": _season_teams(
                    "2020", [{"slot": 4, "nickname": "Q", "name": "N2", "logo": logo}]
                ),
            }
        )
        assert _ids(out, "2019", 4) != _ids(out, "2020", 4)

    def test_two_teams_claiming_one_identity_link_neither(self, processor_handler):
        """Two teams that each match the same earlier person by different values are
        ambiguous, so neither is linked by that signal."""
        out = processor_handler.resolve_yahoo_owner_identities(
            {
                "2019": _season_teams(
                    "2019", [{"slot": 1, "nickname": "Manager A", "name": "Team X"}]
                ),
                "2020": _season_teams(
                    "2020", [{"slot": 1, "nickname": "Manager A", "name": "T1"}]
                ),
                "2021": _season_teams(
                    "2021",
                    [
                        {"slot": 1, "nickname": "Other", "name": "Team X"},
                        {"slot": 2, "nickname": "Manager A", "name": "T2"},
                    ],
                ),
            }
        )
        person = _ids(out, "2019", 1)
        assert _ids(out, "2020", 1) == person
        # Nickname pass links slot 2 first (unambiguous); slot 1 then can't claim it.
        assert _ids(out, "2021", 2) == person
        assert _ids(out, "2021", 1) != person

    def test_legacy_rows_without_guid_fields(self, processor_handler):
        def legacy(season, owner, nickname, slot):
            game = {"2019": "390", "2020": "399"}[season]
            return {
                "members": [{"manager_id": owner, "nickname": nickname}],
                "teams": [
                    {
                        "team_key": f"{game}.l.1.t.{slot}",
                        "name": f"N{season}",
                        "manager_id": owner,
                    }
                ],
            }

        out = processor_handler.resolve_yahoo_owner_identities(
            {
                # Non-numeric legacy manager_id is a real guid; numeric is only a slot.
                "2019": legacy("2019", "GUIDA", "Nick A", 1),
                "2020": legacy("2020", "1", "Nick B", 1),
            }
        )
        assert out[("2019", "390.l.1.t.1")] == "GUIDA"
        assert out[("2020", "399.l.1.t.1")] == "399.l.1.t.1"

    def test_team_without_manager_unmapped(self, processor_handler):
        record = {
            "members": [],
            "teams": [
                {"team_key": "390.l.1.t.1", "name": "Orphan", "manager_id": None}
            ],
        }
        assert processor_handler.resolve_yahoo_owner_identities({"2019": record}) == {}


def _identity_league_raw(seasons):
    """Raw Yahoo records for a synthetic league: each season is ``(teams, champion_slot)``
    with every team playing week 1 and a single title game (week 15) won by the champion."""
    raw = []
    for season, (teams, champ) in seasons.items():
        record = _season_teams(season, teams)
        keys = [t["team_key"] for t in record["teams"]]
        champ_key = next(k for k in keys if k.endswith(f".t.{champ}"))
        other = next(k for k in keys if k != champ_key)
        regular = [
            {
                "week": "1",
                "is_playoffs": "0",
                "is_consolation": "0",
                "winner_team_key": a,
                "teams": [
                    {"team_key": a, "points": "100"},
                    {"team_key": b, "points": "90"},
                ],
            }
            for a, b in zip(keys[::2], keys[1::2])
        ]
        final = {
            "week": "15",
            "is_playoffs": "1",
            "is_consolation": "0",
            "winner_team_key": champ_key,
            "teams": [
                {"team_key": champ_key, "points": "120"},
                {"team_key": other, "points": "110"},
            ],
        }
        raw += [
            {"season": season, "data_type": "teams", "data": record},
            {
                "season": season,
                "data_type": "matchups_week1",
                "data": {"matchups": regular},
            },
            {
                "season": season,
                "data_type": "matchups_week15",
                "data": {"matchups": [final]},
            },
        ]
    return raw


def _standings_from_grouped(processor_handler, grouped):
    con = duckdb.connect()
    for view in ("members", "teams", "matchups"):
        con.register(view, pd.DataFrame(grouped[view]))
    con.register(
        "teams_output", con.sql(processor_handler.QUERIES["TEAMS"]["YAHOO"]).df()
    )
    con.register(
        "matchups_output", con.sql(processor_handler.QUERIES["MATCHUPS"]["YAHOO"]).df()
    )
    df = con.sql(processor_handler.QUERIES["STANDINGS"]).df()
    con.close()
    return df


# Slot 2 changes hands between seasons: Manager B wins 2019 in slot 2 then leaves; Manager C
# takes slot 2 and wins 2020. Manager A moves from slot 1 to slot 3.
_IDENTITY_SEASONS = {
    "2019": (
        [
            {"slot": 1, "nickname": "Manager A"},
            {"slot": 2, "nickname": "Manager B"},
            {"slot": 3, "nickname": "Manager D"},
            {"slot": 4, "nickname": "Manager E"},
        ],
        2,
    ),
    "2020": (
        [
            {"slot": 1, "nickname": "Manager D"},
            {"slot": 2, "nickname": "Manager C"},
            {"slot": 3, "nickname": "Manager A"},
            {"slot": 4, "nickname": "Manager E"},
        ],
        2,
    ),
}


class TestYahooStableOwnersInStandings:
    def test_each_title_credited_to_its_real_winner(self, processor_handler):
        grouped = processor_handler._register_yahoo_raw_data(
            _identity_league_raw(_IDENTITY_SEASONS), {}, {}
        )
        df = _standings_from_grouped(processor_handler, grouped)
        champs = df[df["champion"] == "Yes"].set_index("season")
        assert champs.loc["2019", "owner_username"] == "Manager B"
        assert champs.loc["2020", "owner_username"] == "Manager C"
        assert champs.loc["2019", "owner_id"] != champs.loc["2020", "owner_id"]
        # One owner id per person, one person per owner id.
        assert (df.groupby("owner_id")["owner_username"].nunique() == 1).all()
        assert (df.groupby("owner_username")["owner_id"].nunique() == 1).all()
        assert df["owner_id"].nunique() == 5


class TestYahooIdentitiesOnIncrementalRuns:
    def test_latest_season_alone_keeps_full_run_ids(self, processor_handler):
        raw = _identity_league_raw(_IDENTITY_SEASONS)
        full = processor_handler._register_yahoo_raw_data(raw, {}, {})
        identity_teams = {
            r["season"]: r["data"]
            for r in raw
            if r["data_type"] == "teams" and r["season"] == "2019"
        }
        partial = processor_handler._register_yahoo_raw_data(
            [r for r in raw if r["season"] == "2020"],
            {},
            {},
            identity_teams=identity_teams,
        )

        def owners(grouped):
            return {
                t["id"]: t["primaryOwner"]
                for t in grouped["teams"]
                if t["season"] == "2020"
            }

        assert owners(partial) == owners(full)
        # Without the other seasons, the moved manager would get a fresh id instead.
        alone = processor_handler._register_yahoo_raw_data(
            [r for r in raw if r["season"] == "2020"], {}, {}
        )
        assert owners(alone) != owners(full)

    def test_new_season_keeps_returning_managers(self, processor_handler):
        seasons = {
            **_IDENTITY_SEASONS,
            "2021": (
                [
                    {"slot": 1, "nickname": "Manager C"},
                    {"slot": 2, "nickname": "Manager F"},
                    {"slot": 3, "nickname": "Manager A"},
                    {"slot": 4, "nickname": "Manager E"},
                ],
                1,
            ),
        }
        raw = _identity_league_raw(seasons)
        full = processor_handler._register_yahoo_raw_data(raw, {}, {})
        by_name = {(m["season"], m["displayName"]): m["id"] for m in full["members"]}
        assert by_name[("2021", "Manager C")] == by_name[("2020", "Manager C")]
        assert by_name[("2021", "Manager A")] == by_name[("2019", "Manager A")]
        assert by_name[("2021", "Manager F")] == "406.l.1.t.2"


class TestReadYahooIdentityTeams:
    def test_reads_only_teams_records(self, processor_handler):
        def fake_read(bucket, key):
            season = key.rsplit("/", 1)[-1].removesuffix(".json")
            return [
                {"data_type": "settings", "data": {}},
                {"data_type": "teams", "data": {"teams": [{"team_key": season}]}},
            ]

        with patch.object(processor_handler, "read_s3_object", side_effect=fake_read):
            out = processor_handler.read_yahoo_identity_teams(
                "bucket", "raw/x", ["2019", "2020"]
            )
        assert out == {
            "2019": {"teams": [{"team_key": "2019"}]},
            "2020": {"teams": [{"team_key": "2020"}]},
        }

    def test_no_seasons_reads_nothing(self, processor_handler):
        with patch.object(processor_handler, "read_s3_object") as read:
            assert processor_handler.read_yahoo_identity_teams("b", "p", []) == {}
        read.assert_not_called()

    def test_failed_season_raises(self, processor_handler):
        with (
            patch.object(
                processor_handler, "read_s3_object", side_effect=RuntimeError("S3 down")
            ),
            pytest.raises(RuntimeError, match="2019"),
        ):
            processor_handler.read_yahoo_identity_teams("b", "p", ["2019"])


@pytest.fixture
def migration_table(processor_handler, monkeypatch):
    """A moto DynamoDB table swapped in for the processor's table (created inside mock_aws,
    so no real AWS client is ever built)."""
    import boto3
    from moto import mock_aws

    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        table = ddb.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        with patch.object(processor_handler, "table", table):
            yield table


def _put_mapping(table, sk, new_ids):
    table.put_item(
        Item={
            "PK": "LEAGUE#canon",
            "SK": sk,
            "data": [
                {
                    "currentPlatformOwnerId": f"src-{i}",
                    "newPlatformOwnerId": new_id,
                    "displayName": f"Manager {i}",
                }
                for i, new_id in enumerate(new_ids)
            ],
        }
    )


class TestTranslateYahooMigrationMappings:
    def test_translated_once_then_left_alone(self, processor_handler, migration_table):
        _put_mapping(
            migration_table,
            "PLATFORM_MIGRATION#ESPN#YAHOO",
            ["1", "2", "__not_returning__", "unknown"],
        )
        processor_handler.translate_yahoo_migration_mappings(
            "canon", {"1": "390.l.1.t.4", "2": "GUID2"}
        )
        item = migration_table.get_item(
            Key={"PK": "LEAGUE#canon", "SK": "PLATFORM_MIGRATION#ESPN#YAHOO"}
        )["Item"]
        assert [e["newPlatformOwnerId"] for e in item["data"]] == [
            "390.l.1.t.4",
            "GUID2",
            "__not_returning__",
            "unknown",
        ]
        assert item["yahoo_owner_ids_resolved"] is True

        # A later run (whose latest season may have reassigned slots) changes nothing.
        processor_handler.translate_yahoo_migration_mappings(
            "canon", {"390.l.1.t.4": "WRONG", "1": "WRONG"}
        )
        again = migration_table.get_item(
            Key={"PK": "LEAGUE#canon", "SK": "PLATFORM_MIGRATION#ESPN#YAHOO"}
        )["Item"]
        assert again["data"] == item["data"]

    def test_non_yahoo_destination_untouched(self, processor_handler, migration_table):
        _put_mapping(migration_table, "PLATFORM_MIGRATION#ESPN#SLEEPER", ["1"])
        processor_handler.translate_yahoo_migration_mappings("canon", {"1": "X"})
        item = migration_table.get_item(
            Key={"PK": "LEAGUE#canon", "SK": "PLATFORM_MIGRATION#ESPN#SLEEPER"}
        )["Item"]
        assert item["data"][0]["newPlatformOwnerId"] == "1"
        assert "yahoo_owner_ids_resolved" not in item

    def test_empty_mapping_skips_query(self, processor_handler):
        with patch.object(processor_handler, "table") as table:
            processor_handler.translate_yahoo_migration_mappings("canon", {})
        table.query.assert_not_called()

    def test_concurrent_translation_is_tolerated(self, processor_handler):
        import botocore.exceptions

        table = MagicMock()
        table.query.return_value = {
            "Items": [{"SK": "PLATFORM_MIGRATION#ESPN#YAHOO", "data": []}]
        }
        table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
        )
        with patch.object(processor_handler, "table", table):
            processor_handler.translate_yahoo_migration_mappings("canon", {"1": "X"})

    def test_other_errors_raise(self, processor_handler):
        import botocore.exceptions

        table = MagicMock()
        table.query.return_value = {
            "Items": [{"SK": "PLATFORM_MIGRATION#ESPN#YAHOO", "data": []}]
        }
        table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}}, "UpdateItem"
        )
        with (
            patch.object(processor_handler, "table", table),
            pytest.raises(botocore.exceptions.ClientError),
        ):
            processor_handler.translate_yahoo_migration_mappings("canon", {"1": "X"})


class TestYahooOwnerIdsBySeason:
    def test_raw_to_stable_per_season(self, processor_handler):
        grouped = processor_handler._register_yahoo_raw_data(
            _identity_league_raw(_IDENTITY_SEASONS), {}, {}
        )
        by_season = grouped["yahoo_owner_ids_by_season"]
        # Slot 3 in 2020 is Manager A, who started in slot 1 in 2019.
        assert by_season["2020"]["3"] == by_season["2019"]["1"] == "390.l.1.t.1"
        # Slot 2 in 2020 is a new manager (Manager C).
        assert by_season["2020"]["2"] == "399.l.1.t.2"
