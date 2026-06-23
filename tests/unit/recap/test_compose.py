"""Tests for recap/compose.py — the orchestrator.

Verifies the flow: Bedrock AI generation → numeric validation. There is no
deterministic fallback, so an AI failure, a validation rejection, or an empty week
raises ``RecapGenerationError`` (which the handler records as a failed week).
``ai_generate.generate`` is monkeypatched; the validation gate runs for real.
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
    def test_valid_recap_returns_model(self, recap_compose, monkeypatch):
        monkeypatch.setattr(
            recap_compose.ai_generate,
            "generate",
            lambda h, s, w: {"headline": "AI Headline", "body": "Aces rolled."},
        )
        result = recap_compose.generate_recap(_highlights(), "2025", "1")
        assert result["headline"] == "AI Headline"
        assert result["body"] == "Aces rolled."
        assert result["model"] == recap_compose.ai_generate.MODEL_ID

    def test_valid_ai_numbers_kept(self, recap_compose, monkeypatch):
        # Real scores from the highlights pass validation -> AI recap is kept.
        monkeypatch.setattr(
            recap_compose.ai_generate,
            "generate",
            lambda h, s, w: {
                "headline": "Aces 100-90",
                "body": "Aces beat Bears 100 to 90.",
            },
        )
        result = recap_compose.generate_recap(_highlights(), "2025", "1")
        assert result["model"] == recap_compose.ai_generate.MODEL_ID

    def test_failed_validation_raises(self, recap_compose, monkeypatch):
        # An invented number fails the gate -> no fallback, the week is left failed.
        monkeypatch.setattr(
            recap_compose.ai_generate,
            "generate",
            lambda h, s, w: {
                "headline": "Phantom",
                "body": "Aces piled up 99999 points from nowhere.",
            },
        )
        with pytest.raises(recap_compose.RecapGenerationError):
            recap_compose.generate_recap(_highlights(), "2025", "1")

    def test_ai_error_propagates(self, recap_compose, monkeypatch):
        def _raise(h, s, w):
            raise recap_compose.ai_generate.RecapGenerationError("blocked")

        monkeypatch.setattr(recap_compose.ai_generate, "generate", _raise)
        with pytest.raises(recap_compose.RecapGenerationError):
            recap_compose.generate_recap(_highlights(), "2025", "1")

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

    def test_model_id_re_exported(self, recap_compose):
        assert recap_compose.MODEL_ID == recap_compose.ai_generate.MODEL_ID
