"""Tests for ai_recap/highlights.py (deterministic, no LLM)."""

from decimal import Decimal


def _matchup(
    a_score, b_score, *, a_starters=None, a_bench=None, b_starters=None, b_bench=None
):
    return {
        "team_a_id": "1",
        "team_a_display_name": "alice",
        "team_a_team_name": "Alice's Aces",
        "team_a_score": a_score,
        "team_a_starters": a_starters or [],
        "team_a_bench": a_bench or [],
        "team_b_id": "2",
        "team_b_display_name": "bob",
        "team_b_team_name": "Bob's Bombers",
        "team_b_score": b_score,
        "team_b_starters": b_starters or [],
        "team_b_bench": b_bench or [],
    }


class TestComputeHighlights:
    def test_basic_scores_and_winner(self, ai_recap_highlights):
        h = ai_recap_highlights.compute_highlights(
            [_matchup(Decimal("100.5"), Decimal("90.25"))], [], "2025", "1"
        )
        assert h["season"] == "2025"
        assert h["week"] == "1"
        assert len(h["matchups"]) == 1
        m = h["matchups"][0]
        assert m["winner"] == "alice"
        assert m["loser"] == "bob"
        assert m["margin"] == 10.25
        assert m["tied"] is False
        assert m["team_a"]["score"] == 100.5

    def test_top_scorer_and_bust(self, ai_recap_highlights):
        starters = [
            {"full_name": "QB One", "position": "QB", "points_scored": Decimal("30.5")},
            {"full_name": "RB Two", "position": "RB", "points_scored": Decimal("2.1")},
        ]
        h = ai_recap_highlights.compute_highlights(
            [_matchup(50, 40, a_starters=starters)], [], "2025", "1"
        )
        side = h["matchups"][0]["team_a"]
        assert side["top_scorer"]["name"] == "QB One"
        assert side["top_scorer"]["points"] == 30.5
        assert side["biggest_bust"]["name"] == "RB Two"
        assert side["biggest_bust"]["points"] == 2.1

    def test_fantasy_position_preferred_over_position(self, ai_recap_highlights):
        starters = [
            {
                "full_name": "Flex Guy",
                "position": "RB",
                "fantasy_position": "FLEX",
                "points_scored": 12,
            }
        ]
        h = ai_recap_highlights.compute_highlights(
            [_matchup(50, 40, a_starters=starters)], [], "2025", "1"
        )
        assert h["matchups"][0]["team_a"]["top_scorer"]["position"] == "FLEX"

    def test_bench_points_summed(self, ai_recap_highlights):
        bench = [
            {"full_name": "Bench A", "points_scored": Decimal("5.5")},
            {"full_name": "Bench B", "points_scored": Decimal("4.5")},
        ]
        h = ai_recap_highlights.compute_highlights(
            [_matchup(50, 40, a_bench=bench)], [], "2025", "1"
        )
        assert h["matchups"][0]["team_a"]["points_on_bench"] == 10.0

    def test_no_starters_yields_none(self, ai_recap_highlights):
        h = ai_recap_highlights.compute_highlights([_matchup(50, 40)], [], "2025", "1")
        assert h["matchups"][0]["team_a"]["top_scorer"] is None
        assert h["matchups"][0]["team_a"]["biggest_bust"] is None
        assert h["matchups"][0]["team_a"]["points_on_bench"] == 0.0

    def test_tie_has_no_winner_and_no_margin_entry(self, ai_recap_highlights):
        h = ai_recap_highlights.compute_highlights([_matchup(75, 75)], [], "2025", "1")
        m = h["matchups"][0]
        assert m["tied"] is True
        assert m["winner"] is None
        assert m["loser"] is None
        # A tie contributes no decided margin, so week_extremes is empty.
        assert h["week_extremes"] == {}

    def test_bye_self_matchup_skipped(self, ai_recap_highlights):
        bye = _matchup(100, 0)
        bye["team_b_id"] = "1"  # same as team_a_id → placeholder
        h = ai_recap_highlights.compute_highlights([bye], [], "2025", "1")
        assert h["matchups"] == []
        assert h["week_extremes"] == {}

    def test_week_extremes_biggest_and_closest(self, ai_recap_highlights):
        blowout = _matchup(120, 80)  # margin 40
        close = {
            **_matchup(101, 100),  # margin 1
            "team_a_id": "3",
            "team_a_display_name": "carol",
            "team_b_id": "4",
            "team_b_display_name": "dave",
        }
        h = ai_recap_highlights.compute_highlights([blowout, close], [], "2025", "1")
        assert h["week_extremes"]["biggest_margin"]["margin"] == 40.0
        assert h["week_extremes"]["biggest_margin"]["winner"] == "alice"
        assert h["week_extremes"]["closest_margin"]["margin"] == 1.0
        assert h["week_extremes"]["closest_margin"]["winner"] == "carol"

    def test_standings_filtered_to_week_and_ranked(self, ai_recap_highlights):
        rows = [
            {
                "snapshot_week": "1",
                "owner_username": "bob",
                "team_name": "Bob's Bombers",
                "record": "0-1-0",
                "wins": 0,
                "total_pf": Decimal("90.25"),
            },
            {
                "snapshot_week": "1",
                "owner_username": "alice",
                "team_name": "Alice's Aces",
                "record": "1-0-0",
                "wins": 1,
                "total_pf": Decimal("100.5"),
            },
            {
                "snapshot_week": "2",  # filtered out
                "owner_username": "alice",
                "wins": 2,
                "total_pf": Decimal("200"),
            },
        ]
        h = ai_recap_highlights.compute_highlights(
            [_matchup(100.5, 90.25)], rows, "2025", "1"
        )
        standings = h["standings"]
        assert [s["rank"] for s in standings] == [1, 2]
        assert standings[0]["manager"] == "alice"  # more wins → rank 1
        assert standings[1]["manager"] == "bob"

    def test_empty_week(self, ai_recap_highlights):
        h = ai_recap_highlights.compute_highlights([], [], "2025", "3")
        assert h["matchups"] == []
        assert h["week_extremes"] == {}
        assert h["standings"] == []

    def test_non_numeric_score_coerced_to_zero(self, ai_recap_highlights):
        h = ai_recap_highlights.compute_highlights(
            [_matchup("not-a-number", 50)], [], "2025", "1"
        )
        m = h["matchups"][0]
        assert m["team_a"]["score"] == 0.0
        assert m["winner"] == "bob"
