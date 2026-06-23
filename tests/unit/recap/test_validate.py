"""Tests for recap/validate.py — the numeric guardrail gate.

``validate_recap`` rejects a recap that prints a number the highlights don't
contain (a hallucinated score / stat), tolerating the model rounding a two-decimal
value to a whole number. Names are not gated — only numbers.
"""

import pytest


def _highlights():
    return {
        "season": "2024",
        "week": "3",
        "matchups": [
            {
                "team_a": {
                    "team_name": "Aces",
                    "manager": "alice",
                    "score": 95.46,
                    "top_scorer": {"name": "WR1", "position": "WR", "points": 30.12},
                    "biggest_bust": {"name": "Dud", "position": "TE", "points": 1.5},
                    "points_on_bench": 22.0,
                },
                "team_b": {
                    "team_name": "Bears",
                    "manager": "bob",
                    "score": 90.12,
                    "top_scorer": {"name": "RB1", "position": "RB", "points": 18.0},
                    "biggest_bust": None,
                    "points_on_bench": 4.0,
                },
                "margin": 5.34,
                "tied": False,
            }
        ],
        "standings": [
            {"rank": 1, "manager": "alice", "record": "2-1", "points_for": 280.0}
        ],
    }


class TestValidateRecap:
    def test_accepts_exact_numbers(self, recap_validate):
        recap = {
            "headline": "Aces edge Bears",
            "body": "Aces won 95.46 to 90.12, a 5.34-point margin. WR1 had 30.12.",
        }
        assert recap_validate.validate_recap(recap, _highlights()) is True

    def test_accepts_whole_number_rounding(self, recap_validate):
        # The model rounded 95.46 -> 95 and 90.12 -> 90; within tolerance.
        recap = {"headline": "95-90 win", "body": "Aces beat Bears 95 to 90."}
        assert recap_validate.validate_recap(recap, _highlights()) is True

    def test_rejects_invented_number(self, recap_validate):
        recap = {
            "headline": "Aces win",
            "body": "WR1 racked up 230 yards on 12 carries.",
        }
        assert recap_validate.validate_recap(recap, _highlights()) is False

    def test_accepts_record_parts(self, recap_validate):
        # The record string "2-1" contributes both 2 and 1 as legal numbers.
        recap = {"headline": "Top dog", "body": "alice improved to 2-1 on the year."}
        assert recap_validate.validate_recap(recap, _highlights()) is True

    def test_accepts_season_and_week(self, recap_validate):
        recap = {"headline": "Week 3", "body": "The 2024 season rolls on in week 3."}
        assert recap_validate.validate_recap(recap, _highlights()) is True

    def test_accepts_text_with_no_numbers(self, recap_validate):
        recap = {"headline": "A clash for the ages", "body": "Aces topped Bears."}
        assert recap_validate.validate_recap(recap, _highlights()) is True

    def test_rejects_when_any_number_unsupported(self, recap_validate):
        # All but one number are legal — a single invented figure still fails.
        recap = {
            "headline": "Aces win 95-90",
            "body": "Aces 95.46, Bears 90.12, and a phantom 777 from nowhere.",
        }
        assert recap_validate.validate_recap(recap, _highlights()) is False

    def test_missing_keys_default_empty(self, recap_validate):
        assert recap_validate.validate_recap({}, _highlights()) is True


class TestCollectFacts:
    def test_ignores_booleans(self, recap_validate):
        facts = set()
        recap_validate._collect_facts({"flag": True, "n": 7}, facts)
        assert 7.0 in facts
        assert 1.0 not in facts  # True must not leak in as 1

    def test_parses_numbers_from_strings(self, recap_validate):
        facts = set()
        recap_validate._collect_facts({"record": "10-3", "season": "2024"}, facts)
        assert {10.0, 3.0, 2024.0} <= facts

    def test_walks_nested_lists(self, recap_validate):
        facts = set()
        recap_validate._collect_facts([{"a": [1, 2]}, {"b": 3}], facts)
        assert {1.0, 2.0, 3.0} <= facts


@pytest.mark.parametrize(
    "value,expected",
    [(95.46, True), (95.0, True), (95.96, True), (96.5, False), (777.0, False)],
)
def test_matches_tolerance(recap_validate, value, expected):
    facts = {95.46}
    assert recap_validate._matches(value, facts) is expected
