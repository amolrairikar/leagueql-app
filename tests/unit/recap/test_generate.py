"""Tests for recap/generate.py — the deterministic snippet composer.

No LLM, no network: composition is a pure function of the highlights dict and a
hash-seeded RNG, so these tests assert determinism, variety, correct framing per
situation, and that no template ships with an unfillable placeholder.
"""

import random

import pytest


# --- builders ---------------------------------------------------------------


def _player(name="Star Player", position="RB", points=25.0):
    return {"name": name, "position": position, "points": points}


def _team(name, mgr, score, top=None, bust=None, bench=0.0):
    return {
        "team_name": name,
        "manager": mgr,
        "score": score,
        "top_scorer": top,
        "biggest_bust": bust,
        "points_on_bench": bench,
    }


def _matchup(a, b, is_playoff=False, round_name=None):
    if a["score"] > b["score"]:
        winner, loser = a["manager"], b["manager"]
    elif b["score"] > a["score"]:
        winner, loser = b["manager"], a["manager"]
    else:
        winner = loser = None
    return {
        "team_a": a,
        "team_b": b,
        "winner": winner,
        "loser": loser,
        "margin": round(abs(a["score"] - b["score"]), 2),
        "tied": a["score"] == b["score"],
        "is_playoff": is_playoff,
        "playoff_tier_type": "WINNERS_BRACKET" if is_playoff else "NONE",
        "playoff_round": round_name,
    }


def _highlights(
    matchups, season="2025", week="1", is_playoff_week=False, extremes=None
):
    return {
        "season": season,
        "week": week,
        "is_playoff_week": is_playoff_week,
        "matchups": matchups,
        "week_extremes": extremes or {},
        "standings": [],
    }


def _simple_week(winner_score=100, loser_score=90, **kw):
    a = _team("Aces", "alice", winner_score, top=_player("WR1", "WR", 30.0))
    b = _team("Bears", "bob", loser_score, bust=_player("Dud", "TE", 1.0))
    return _highlights([_matchup(a, b, **kw)])


def _formatted(templates, **ctx):
    return {t.format(**ctx) for t in templates}


# --- generate_recap (end to end) -------------------------------------------


class TestGenerateRecap:
    def test_returns_headline_and_body(self, recap_generate):
        result = recap_generate.generate_recap(_simple_week(), "2025", "1")
        assert set(result) == {"headline", "body"}
        assert result["headline"]
        assert result["body"]

    def test_no_placeholder_leaks(self, recap_generate):
        result = recap_generate.generate_recap(_simple_week(), "2025", "1")
        for value in result.values():
            assert "{" not in value and "}" not in value

    def test_real_numbers_appear_unaltered(self, recap_generate):
        result = recap_generate.generate_recap(_simple_week(123, 90), "2025", "1")
        # The exact scores from highlights show up verbatim — nothing invented.
        assert "123" in result["body"]
        assert "90" in result["body"]

    def test_deterministic(self, recap_generate):
        h = _simple_week()
        first = recap_generate.generate_recap(h, "2025", "1")
        second = recap_generate.generate_recap(h, "2025", "1")
        assert first == second

    def test_varies_across_weeks(self, recap_generate):
        bodies = {
            recap_generate.generate_recap(_simple_week(), "2025", str(w))["body"]
            for w in range(1, 8)
        }
        assert len(bodies) > 1

    @pytest.mark.parametrize("margin", [1, 5, 15, 30, 60])
    def test_every_margin_bucket_renders(self, recap_generate, margin):
        result = recap_generate.generate_recap(
            _simple_week(100 + margin, 100), "2025", "1"
        )
        assert result["body"]
        assert "{" not in result["body"]

    def test_tie_renders_without_winner_framing(self, recap_generate):
        a = _team("Aces", "alice", 99, top=_player())
        b = _team("Bears", "bob", 99, top=_player("WR9", "WR", 10.0))
        result = recap_generate.generate_recap(
            _highlights([_matchup(a, b)]), "2025", "1"
        )
        assert "99" in result["body"]
        assert "{" not in result["body"]

    def test_multiple_matchups_separated_by_blank_line(self, recap_generate):
        a1 = _team("Aces", "alice", 100, top=_player())
        b1 = _team("Bears", "bob", 80)
        a2 = _team("Cobras", "carol", 110, top=_player("QB1", "QB", 28.0))
        b2 = _team("Ducks", "dave", 95)
        h = _highlights([_matchup(a1, b1), _matchup(a2, b2)])
        body = recap_generate.generate_recap(h, "2025", "1")["body"]
        assert "\n\n" in body

    def test_empty_matchups_raises(self, recap_generate):
        with pytest.raises(recap_generate.RecapGenerationError):
            recap_generate.generate_recap(_highlights([]), "2025", "1")

    def test_missing_matchups_key_raises(self, recap_generate):
        with pytest.raises(recap_generate.RecapGenerationError):
            recap_generate.generate_recap({}, "2025", "1")

    def test_model_id_is_snippet_sentinel(self, recap_generate):
        assert recap_generate.MODEL_ID == "snippet-v1"


# --- result sentence framing ------------------------------------------------


class TestResultSentence:
    def test_tie_branch(self, recap_generate, recap_snippets):
        w = _team("Aces", "alice", 88)
        lo = _team("Bears", "bob", 88)
        out = recap_generate._result_sentence(
            random.Random(0), w, lo, 0, True, False, None
        )
        expected = _formatted(
            recap_snippets.RESULT["tie"], team_a="Aces", team_b="Bears", score="88"
        )
        assert out in expected

    @pytest.mark.parametrize(
        "round_name,group",
        [
            ("Championship", "championship"),
            ("Finals", "championship"),
            ("Semifinals", "advance"),
        ],
    )
    def test_playoff_round_branches(
        self, recap_generate, recap_snippets, round_name, group
    ):
        w = _team("Aces", "alice", 120)
        lo = _team("Bears", "bob", 100)
        out = recap_generate._result_sentence(
            random.Random(0), w, lo, 20, False, True, round_name
        )
        ctx = dict(
            winner="Aces",
            loser="Bears",
            winner_score="120",
            loser_score="100",
            margin="20",
            round=round_name,
        )
        assert out in _formatted(recap_snippets.PLAYOFF_RESULT[group], **ctx)

    def test_playoff_without_round_uses_generic(self, recap_generate, recap_snippets):
        w = _team("Aces", "alice", 120)
        lo = _team("Bears", "bob", 100)
        out = recap_generate._result_sentence(
            random.Random(0), w, lo, 20, False, True, None
        )
        ctx = dict(
            winner="Aces",
            loser="Bears",
            winner_score="120",
            loser_score="100",
            margin="20",
            round="",
        )
        assert out in _formatted(
            recap_snippets.PLAYOFF_RESULT["advance_generic"], **ctx
        )


# --- helpers ----------------------------------------------------------------


class TestHelpers:
    @pytest.mark.parametrize(
        "value,expected",
        [(100.0, "100"), (90.5, "90.5"), (0, "0"), (12.34, "12.34"), (100, "100")],
    )
    def test_fmt(self, recap_generate, value, expected):
        assert recap_generate._fmt(value) == expected

    def test_name_prefers_team_name(self, recap_generate):
        assert recap_generate._name(_team("Aces", "alice", 1)) == "Aces"

    def test_name_falls_back_to_manager(self, recap_generate):
        side = {"team_name": None, "manager": "alice"}
        assert recap_generate._name(side) == "alice"

    def test_name_default(self, recap_generate):
        assert recap_generate._name({}) == "a team"

    @pytest.mark.parametrize(
        "round_name,expected",
        [
            ("Championship", True),
            ("Finals", True),
            ("Final", True),
            ("Semifinals", False),
            ("Quarterfinals", False),
            (None, False),
            ("", False),
        ],
    )
    def test_is_championship(self, recap_generate, round_name, expected):
        assert recap_generate._is_championship(round_name) is expected

    @pytest.mark.parametrize(
        "margin,bucket",
        [
            (2.99, "nailbiter"),
            (3, "close"),
            (9.99, "close"),
            (10, "solid"),
            (19.99, "solid"),
            (20, "comfortable"),
            (39.99, "comfortable"),
            (40, "blowout"),
        ],
    )
    def test_bucket(self, recap_generate, margin, bucket):
        assert recap_generate._bucket(margin) == bucket

    def test_best_scorer_none_when_no_starters(self, recap_generate):
        w = _team("Aces", "alice", 100)
        lo = _team("Bears", "bob", 90)
        assert recap_generate._best_scorer(w, lo) is None

    def test_best_scorer_picks_higher(self, recap_generate):
        w = _team("Aces", "alice", 100, top=_player("WR1", "WR", 30.0))
        lo = _team("Bears", "bob", 90, top=_player("RB1", "RB", 40.0))
        scorer, team = recap_generate._best_scorer(w, lo)
        assert scorer["name"] == "RB1"
        assert team == "Bears"


# --- standout / flavor branches --------------------------------------------


class TestStandout:
    def test_with_position(self, recap_generate, recap_snippets):
        w = _team("Aces", "alice", 100, top=_player("WR1", "WR", 30.0))
        lo = _team("Bears", "bob", 90)
        out = recap_generate._standout_sentence(random.Random(0), w, lo)
        assert out in _formatted(
            recap_snippets.STANDOUT_WITH_POS,
            player="WR1",
            points="30",
            team="Aces",
            position="WR",
        )

    def test_without_position(self, recap_generate, recap_snippets):
        w = _team("Aces", "alice", 100, top=_player("WR1", None, 30.0))
        lo = _team("Bears", "bob", 90)
        out = recap_generate._standout_sentence(random.Random(0), w, lo)
        assert out in _formatted(
            recap_snippets.STANDOUT, player="WR1", points="30", team="Aces"
        )

    def test_none_when_no_starters(self, recap_generate):
        w = _team("Aces", "alice", 100)
        lo = _team("Bears", "bob", 90)
        assert recap_generate._standout_sentence(random.Random(0), w, lo) is None


class TestFlavor:
    def test_none_when_nothing_eligible(self, recap_generate):
        # A tie with negligible bench leaves no flavor option.
        w = _team("Aces", "alice", 88, bench=1.0)
        lo = _team("Bears", "bob", 88, bench=1.0)
        assert (
            recap_generate._flavor_sentence(random.Random(0), w, lo, True, False)
            is None
        )

    def test_all_branches_reachable(self, recap_generate, recap_snippets):
        # Winner has a bench worth calling out; loser has a bust; playoff game →
        # trash, bust, eliminated and bench are all eligible. Sweep seeds so each
        # format branch (and the no-flavor slot) is exercised.
        w = _team("Aces", "alice", 120, bench=35.0)
        lo = _team("Bears", "bob", 100, bust=_player("Dud", "TE", 2.0))
        results = [
            recap_generate._flavor_sentence(random.Random(s), w, lo, False, True)
            for s in range(80)
        ]
        bust = _formatted(
            recap_snippets.FLAVOR["bust"], team="Bears", player="Dud", points="2"
        )
        bench = _formatted(recap_snippets.FLAVOR["bench"], team="Aces", bench="35")
        trash = _formatted(
            recap_snippets.FLAVOR["trash"],
            loser="Bears",
            loser_mgr="bob",
            winner="Aces",
        )
        elim = _formatted(
            recap_snippets.FLAVOR["eliminated"], loser="Bears", loser_mgr="bob"
        )
        produced = set(results)
        assert produced & bust
        assert produced & bench
        assert produced & trash
        assert produced & elim
        assert None in results

    def test_bench_uses_higher_bench_side(self, recap_generate, recap_snippets):
        # Only the loser benched a meaningful total; a tie keeps trash/bust out so
        # bench is the sole eligible flavor.
        w = _team("Aces", "alice", 88, bench=2.0)
        lo = _team("Bears", "bob", 88, bench=40.0)
        seen = {
            recap_generate._flavor_sentence(random.Random(s), w, lo, True, False)
            for s in range(40)
        }
        bench = _formatted(recap_snippets.FLAVOR["bench"], team="Bears", bench="40")
        assert seen & bench


# --- week-extreme tags & headlines -----------------------------------------


class TestExtremeTags:
    def test_biggest_and_closest_tagged(self, recap_generate):
        a1 = _team("Aces", "alice", 150, top=_player())
        b1 = _team("Bears", "bob", 90)
        a2 = _team("Cobras", "carol", 101, top=_player("QB1", "QB", 20.0))
        b2 = _team("Ducks", "dave", 100)
        m1 = _matchup(a1, b1)
        m2 = _matchup(a2, b2)
        extremes = {
            "biggest_margin": {"winner": "alice", "loser": "bob", "margin": 60},
            "closest_margin": {"winner": "carol", "loser": "dave", "margin": 1},
        }
        tags = recap_generate._extreme_tags(_highlights([m1, m2], extremes=extremes))
        assert tags == {0: "biggest", 1: "closest"}

    def test_single_decided_game_tagged_biggest(self, recap_generate):
        a = _team("Aces", "alice", 120, top=_player())
        b = _team("Bears", "bob", 100)
        m = _matchup(a, b)
        extremes = {
            "biggest_margin": {"winner": "alice", "loser": "bob", "margin": 20},
            "closest_margin": {"winner": "alice", "loser": "bob", "margin": 20},
        }
        tags = recap_generate._extreme_tags(_highlights([m], extremes=extremes))
        assert tags == {0: "biggest"}

    def test_no_extremes(self, recap_generate):
        a = _team("Aces", "alice", 88)
        b = _team("Bears", "bob", 88)
        tags = recap_generate._extreme_tags(_highlights([_matchup(a, b)]))
        assert tags == {}

    def test_extreme_tag_appears_in_body(self, recap_generate, recap_snippets):
        a = _team("Aces", "alice", 150, top=_player())
        b = _team("Bears", "bob", 90)
        extremes = {"biggest_margin": {"winner": "alice", "loser": "bob", "margin": 60}}
        body = recap_generate.generate_recap(
            _highlights([_matchup(a, b)], extremes=extremes), "2025", "1"
        )["body"]
        assert any(tag in body for tag in recap_snippets.WEEK_EXTREME["biggest"])


class TestHeadline:
    def _h(self, recap_generate, highlights):
        return recap_generate._headline(random.Random(0), highlights)

    def test_championship_group(self, recap_generate, recap_snippets):
        a = _team("Aces", "alice", 120, top=_player())
        b = _team("Bears", "bob", 100)
        h = _highlights(
            [_matchup(a, b, is_playoff=True, round_name="Championship")],
            is_playoff_week=True,
        )
        assert self._h(recap_generate, h) in recap_snippets.HEADLINES["championship"]

    def test_playoff_group(self, recap_generate, recap_snippets):
        a = _team("Aces", "alice", 120, top=_player())
        b = _team("Bears", "bob", 100)
        h = _highlights(
            [_matchup(a, b, is_playoff=True, round_name="Semifinals")],
            is_playoff_week=True,
        )
        assert self._h(recap_generate, h) in recap_snippets.HEADLINES["playoff"]

    def test_blowout_group(self, recap_generate, recap_snippets):
        a = _team("Aces", "alice", 160, top=_player())
        b = _team("Bears", "bob", 100)
        h = _highlights([_matchup(a, b)])
        assert self._h(recap_generate, h) in recap_snippets.HEADLINES["blowout"]

    def test_general_group(self, recap_generate, recap_snippets):
        a = _team("Aces", "alice", 105, top=_player())
        b = _team("Bears", "bob", 100)
        h = _highlights([_matchup(a, b)])
        assert self._h(recap_generate, h) in recap_snippets.HEADLINES["general"]
