"""Tests for Yahoo processing: _register_yahoo_raw_data + YAHOO query transforms."""

import duckdb
import pandas as pd


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
