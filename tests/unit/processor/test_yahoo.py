"""Tests for Yahoo processing: _register_yahoo_raw_data + YAHOO query transforms."""

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
