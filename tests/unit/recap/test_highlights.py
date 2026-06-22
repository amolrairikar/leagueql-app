"""Tests for recap/highlights.py (deterministic, no LLM)."""

from decimal import Decimal


def _matchup(
    a_score,
    b_score,
    *,
    a_starters=None,
    a_bench=None,
    b_starters=None,
    b_bench=None,
    playoff_tier_type=None,
    playoff_round=None,
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
        "playoff_tier_type": playoff_tier_type,
        "playoff_round": playoff_round,
    }


class TestComputeHighlights:
    def test_basic_scores_and_winner(self, recap_highlights):
        h = recap_highlights.compute_highlights(
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
        # Regular-season game: no playoff context, week not flagged.
        assert m["is_playoff"] is False
        assert m["playoff_tier_type"] == "NONE"
        assert m["playoff_round"] is None
        assert h["is_playoff_week"] is False

    def test_regular_season_with_missing_playoff_fields(self, recap_highlights):
        # An older matchup row without the playoff keys defaults to regular-season.
        bare = _matchup(50, 40)
        del bare["playoff_tier_type"]
        del bare["playoff_round"]
        h = recap_highlights.compute_highlights([bare], [], "2025", "1")
        assert h["is_playoff_week"] is False
        assert h["matchups"][0]["is_playoff"] is False
        assert h["matchups"][0]["playoff_tier_type"] == "NONE"

    def test_playoff_matchup_carries_round_and_flags_week(self, recap_highlights):
        h = recap_highlights.compute_highlights(
            [
                _matchup(
                    110,
                    100,
                    playoff_tier_type="WINNERS_BRACKET",
                    playoff_round="Championship",
                )
            ],
            [],
            "2025",
            "16",
        )
        assert h["is_playoff_week"] is True
        m = h["matchups"][0]
        assert m["is_playoff"] is True
        assert m["playoff_tier_type"] == "WINNERS_BRACKET"
        assert m["playoff_round"] == "Championship"
        assert m["winner"] == "alice"
        assert m["loser"] == "bob"

    def test_mixed_week_flags_playoff_when_any_game_is_postseason(
        self, recap_highlights
    ):
        regular = _matchup(50, 40)
        playoff = {
            **_matchup(
                90, 80, playoff_tier_type="WINNERS_BRACKET", playoff_round="Semifinals"
            ),
            "team_a_id": "3",
            "team_a_display_name": "carol",
            "team_b_id": "4",
            "team_b_display_name": "dave",
        }
        h = recap_highlights.compute_highlights([regular, playoff], [], "2025", "15")
        assert h["is_playoff_week"] is True
        by_winner = {m["winner"]: m for m in h["matchups"]}
        assert by_winner["alice"]["is_playoff"] is False
        assert by_winner["carol"]["is_playoff"] is True
        assert by_winner["carol"]["playoff_round"] == "Semifinals"

    def test_top_scorer_and_bust(self, recap_highlights):
        starters = [
            {"full_name": "QB One", "position": "QB", "points_scored": Decimal("30.5")},
            {"full_name": "RB Two", "position": "RB", "points_scored": Decimal("2.1")},
        ]
        h = recap_highlights.compute_highlights(
            [_matchup(50, 40, a_starters=starters)], [], "2025", "1"
        )
        side = h["matchups"][0]["team_a"]
        assert side["top_scorer"]["name"] == "QB One"
        assert side["top_scorer"]["points"] == 30.5
        assert side["biggest_bust"]["name"] == "RB Two"
        assert side["biggest_bust"]["points"] == 2.1

    def test_fantasy_position_preferred_over_position(self, recap_highlights):
        starters = [
            {
                "full_name": "Flex Guy",
                "position": "RB",
                "fantasy_position": "FLEX",
                "points_scored": 12,
            }
        ]
        h = recap_highlights.compute_highlights(
            [_matchup(50, 40, a_starters=starters)], [], "2025", "1"
        )
        assert h["matchups"][0]["team_a"]["top_scorer"]["position"] == "FLEX"

    def test_bench_points_summed(self, recap_highlights):
        bench = [
            {"full_name": "Bench A", "points_scored": Decimal("5.5")},
            {"full_name": "Bench B", "points_scored": Decimal("4.5")},
        ]
        h = recap_highlights.compute_highlights(
            [_matchup(50, 40, a_bench=bench)], [], "2025", "1"
        )
        assert h["matchups"][0]["team_a"]["points_on_bench"] == 10.0

    def test_no_starters_yields_none(self, recap_highlights):
        h = recap_highlights.compute_highlights([_matchup(50, 40)], [], "2025", "1")
        assert h["matchups"][0]["team_a"]["top_scorer"] is None
        assert h["matchups"][0]["team_a"]["biggest_bust"] is None
        assert h["matchups"][0]["team_a"]["points_on_bench"] == 0.0

    def test_tie_has_no_winner_and_no_margin_entry(self, recap_highlights):
        h = recap_highlights.compute_highlights([_matchup(75, 75)], [], "2025", "1")
        m = h["matchups"][0]
        assert m["tied"] is True
        assert m["winner"] is None
        assert m["loser"] is None
        # A tie contributes no decided margin, so week_extremes is empty.
        assert h["week_extremes"] == {}

    def test_bye_self_matchup_skipped(self, recap_highlights):
        bye = _matchup(100, 0)
        bye["team_b_id"] = "1"  # same as team_a_id → placeholder
        h = recap_highlights.compute_highlights([bye], [], "2025", "1")
        assert h["matchups"] == []
        assert h["week_extremes"] == {}

    def test_week_extremes_biggest_and_closest(self, recap_highlights):
        blowout = _matchup(120, 80)  # margin 40
        close = {
            **_matchup(101, 100),  # margin 1
            "team_a_id": "3",
            "team_a_display_name": "carol",
            "team_b_id": "4",
            "team_b_display_name": "dave",
        }
        h = recap_highlights.compute_highlights([blowout, close], [], "2025", "1")
        assert h["week_extremes"]["biggest_margin"]["margin"] == 40.0
        assert h["week_extremes"]["biggest_margin"]["winner"] == "alice"
        assert h["week_extremes"]["closest_margin"]["margin"] == 1.0
        assert h["week_extremes"]["closest_margin"]["winner"] == "carol"

    def test_standings_filtered_to_week_and_ranked(self, recap_highlights):
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
        h = recap_highlights.compute_highlights(
            [_matchup(100.5, 90.25)], rows, "2025", "1"
        )
        standings = h["standings"]
        assert [s["rank"] for s in standings] == [1, 2]
        assert standings[0]["manager"] == "alice"  # more wins → rank 1
        assert standings[1]["manager"] == "bob"

    def test_empty_week(self, recap_highlights):
        h = recap_highlights.compute_highlights([], [], "2025", "3")
        assert h["matchups"] == []
        assert h["week_extremes"] == {}
        assert h["standings"] == []

    def test_non_numeric_score_coerced_to_zero(self, recap_highlights):
        h = recap_highlights.compute_highlights(
            [_matchup("not-a-number", 50)], [], "2025", "1"
        )
        m = h["matchups"][0]
        assert m["team_a"]["score"] == 0.0
        assert m["winner"] == "bob"
