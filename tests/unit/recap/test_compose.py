"""Tests for recap/compose.py — the orchestrator.

Verifies the four-step flow: deterministic outline → Bedrock AI → numeric
validation → snippet fallback. ``ai_generate.generate`` is monkeypatched; the
validation gate and the snippet composer run for real.
"""

import pytest


def _player(name="WR1", position="WR", points=30.0):
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


def _matchup(a, b):
    winner, loser = (a, b) if a["score"] >= b["score"] else (b, a)
    return {
        "team_a": a,
        "team_b": b,
        "winner": winner["manager"],
        "loser": loser["manager"],
        "margin": round(abs(a["score"] - b["score"]), 2),
        "tied": False,
        "is_playoff": False,
        "playoff_tier_type": "NONE",
        "playoff_round": None,
    }


def _highlights(matchups=None):
    if matchups is None:
        a = _team("Aces", "alice", 100, top=_player())
        b = _team("Bears", "bob", 90, bust=_player("Dud", "TE", 1.0))
        matchups = [_matchup(a, b)]
    return {
        "season": "2025",
        "week": "1",
        "is_playoff_week": False,
        "matchups": matchups,
        "week_extremes": {},
        "standings": [],
    }


class TestGenerateRecap:
    def test_ai_success_returns_ai_model(self, recap_compose, monkeypatch):
        monkeypatch.setattr(
            recap_compose.ai_generate,
            "generate",
            lambda h, o, s, w: {"headline": "AI Headline", "body": "Aces rolled."},
        )
        result = recap_compose.generate_recap(_highlights(), "2025", "1")
        assert result["headline"] == "AI Headline"
        assert result["body"] == "Aces rolled."
        assert result["model"] == recap_compose.ai_generate.MODEL_ID

    def test_ai_error_falls_back_to_snippet(self, recap_compose, monkeypatch):
        def _raise(h, o, s, w):
            raise recap_compose.ai_generate.RecapGenerationError("blocked")

        monkeypatch.setattr(recap_compose.ai_generate, "generate", _raise)
        result = recap_compose.generate_recap(_highlights(), "2025", "1")
        assert result["model"] == "snippet-v1"
        assert result["headline"] and result["body"]

    def test_unexpected_ai_error_falls_back(self, recap_compose, monkeypatch):
        def _boom(h, o, s, w):
            raise RuntimeError("throttled")

        monkeypatch.setattr(recap_compose.ai_generate, "generate", _boom)
        result = recap_compose.generate_recap(_highlights(), "2025", "1")
        assert result["model"] == "snippet-v1"
        assert result["body"]

    def test_failed_validation_falls_back(self, recap_compose, monkeypatch):
        # An invented number fails the gate -> deterministic fallback.
        monkeypatch.setattr(
            recap_compose.ai_generate,
            "generate",
            lambda h, o, s, w: {
                "headline": "Phantom",
                "body": "Aces piled up 99999 points from nowhere.",
            },
        )
        result = recap_compose.generate_recap(_highlights(), "2025", "1")
        assert result["model"] == "snippet-v1"

    def test_valid_ai_numbers_kept(self, recap_compose, monkeypatch):
        # Real scores from the highlights pass validation -> AI recap is kept.
        monkeypatch.setattr(
            recap_compose.ai_generate,
            "generate",
            lambda h, o, s, w: {
                "headline": "Aces 100-90",
                "body": "Aces beat Bears 100 to 90.",
            },
        )
        result = recap_compose.generate_recap(_highlights(), "2025", "1")
        assert result["model"] == recap_compose.ai_generate.MODEL_ID

    def test_no_matchups_skips_ai_and_raises(self, recap_compose, monkeypatch):
        called = []
        monkeypatch.setattr(
            recap_compose.ai_generate,
            "generate",
            lambda *a, **k: called.append(1) or {"headline": "x", "body": "y"},
        )
        with pytest.raises(recap_compose.RecapGenerationError):
            recap_compose.generate_recap(_highlights(matchups=[]), "2025", "1")
        assert called == []  # AI never invoked for an empty week
