"""Tests for recap/outline.py — the deterministic story plan.

``build_outline`` is a pure function of the highlights dict: it fixes the headline
angle, orders matchups by narrative significance, and surfaces the beats (standout,
bust, bench, playoff stakes) the AI writes around. These tests assert that ordering,
the angle selection, and the per-matchup beat fields.
"""


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


def _matchup(a, b, tier="NONE", round_name=None):
    tied = a["score"] == b["score"]
    if tied:
        winner = loser = None
    elif a["score"] > b["score"]:
        winner, loser = a["manager"], b["manager"]
    else:
        winner, loser = b["manager"], a["manager"]
    return {
        "team_a": a,
        "team_b": b,
        "winner": winner,
        "loser": loser,
        "margin": round(abs(a["score"] - b["score"]), 2),
        "tied": tied,
        "is_playoff": tier != "NONE",
        "playoff_tier_type": tier,
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
        "standings": [{"rank": 1, "manager": "alice", "record": "1-0"}],
    }


class TestBuildOutline:
    def test_carries_week_metadata(self, recap_outline):
        a = _team("Aces", "alice", 100, top=_player())
        b = _team("Bears", "bob", 90)
        out = recap_outline.build_outline(_highlights([_matchup(a, b)]))
        assert out["season"] == "2025"
        assert out["week"] == "1"
        assert out["standings"]
        assert len(out["matchups"]) == 1

    def test_orders_matchups_by_significance(self, recap_outline):
        # A 60-point blowout outranks a 1-point nailbiter regardless of input order.
        close_a = _team("Cobras", "carol", 101, top=_player("QB1", "QB", 20.0))
        close_b = _team("Ducks", "dave", 100)
        blow_a = _team("Aces", "alice", 150, top=_player())
        blow_b = _team("Bears", "bob", 90)
        out = recap_outline.build_outline(
            _highlights([_matchup(close_a, close_b), _matchup(blow_a, blow_b)])
        )
        assert out["matchups"][0]["winner"] == "Aces"
        assert out["matchups"][1]["winner"] == "Cobras"

    def test_title_game_ranks_above_bigger_regular_blowout(self, recap_outline):
        reg_a = _team("Aces", "alice", 170, top=_player())
        reg_b = _team("Bears", "bob", 90)
        title_a = _team("Cobras", "carol", 105, top=_player("QB1", "QB", 20.0))
        title_b = _team("Ducks", "dave", 100)
        out = recap_outline.build_outline(
            _highlights(
                [
                    _matchup(reg_a, reg_b),
                    _matchup(
                        title_a, title_b, tier="WINNERS_BRACKET", round_name="Finals"
                    ),
                ],
                is_playoff_week=True,
            )
        )
        assert out["matchups"][0]["winner"] == "Cobras"
        assert out["matchups"][0]["is_championship"] is True

    def test_headline_angle_championship(self, recap_outline):
        a = _team("Aces", "alice", 120, top=_player())
        b = _team("Bears", "bob", 100)
        out = recap_outline.build_outline(
            _highlights(
                [_matchup(a, b, tier="WINNERS_BRACKET", round_name="Championship")],
                is_playoff_week=True,
            )
        )
        assert out["headline_angle"] == "championship"

    def test_headline_angle_playoff(self, recap_outline):
        a = _team("Aces", "alice", 120, top=_player())
        b = _team("Bears", "bob", 100)
        out = recap_outline.build_outline(
            _highlights(
                [_matchup(a, b, tier="WINNERS_BRACKET", round_name="Semifinals")],
                is_playoff_week=True,
            )
        )
        assert out["headline_angle"] == "playoff"

    def test_headline_angle_blowout(self, recap_outline):
        a = _team("Aces", "alice", 160, top=_player())
        b = _team("Bears", "bob", 100)
        out = recap_outline.build_outline(_highlights([_matchup(a, b)]))
        assert out["headline_angle"] == "blowout"

    def test_headline_angle_general(self, recap_outline):
        a = _team("Aces", "alice", 105, top=_player())
        b = _team("Bears", "bob", 100)
        out = recap_outline.build_outline(_highlights([_matchup(a, b)]))
        assert out["headline_angle"] == "general"

    def test_consolation_week_is_not_playoff_angle(self, recap_outline):
        a = _team("Aces", "alice", 105, top=_player())
        b = _team("Bears", "bob", 100)
        out = recap_outline.build_outline(
            _highlights(
                [_matchup(a, b, tier="LOSERS_BRACKET", round_name="Losers Bracket")],
                is_playoff_week=True,
            )
        )
        assert out["headline_angle"] == "general"
        assert out["matchups"][0]["is_consolation"] is True
        assert out["matchups"][0]["is_title_game"] is False

    def test_beat_includes_standout_bust_and_bench(self, recap_outline):
        a = _team("Aces", "alice", 120, top=_player("WR1", "WR", 30.0), bench=35.0)
        b = _team("Bears", "bob", 100, bust=_player("Dud", "TE", 2.0))
        beat = recap_outline.build_outline(_highlights([_matchup(a, b)]))["matchups"][0]
        assert beat["standout"] == {
            "player": "WR1",
            "position": "WR",
            "points": 30.0,
            "team": "Aces",
        }
        assert beat["bust"] == {"team": "Bears", "player": "Dud", "points": 2.0}
        assert beat["bench"] == {"team": "Aces", "points": 35.0}
        assert beat["result_kind"] == "comfortable"

    def test_beat_omits_callouts_when_absent(self, recap_outline):
        a = _team("Aces", "alice", 105)
        b = _team("Bears", "bob", 100)
        beat = recap_outline.build_outline(_highlights([_matchup(a, b)]))["matchups"][0]
        assert "standout" not in beat
        assert "bust" not in beat
        assert "bench" not in beat

    def test_tie_beat(self, recap_outline):
        a = _team("Aces", "alice", 99, top=_player())
        b = _team("Bears", "bob", 99, bust=_player("Dud", "TE", 1.0))
        beat = recap_outline.build_outline(_highlights([_matchup(a, b)]))["matchups"][0]
        assert beat["tied"] is True
        assert beat["result_kind"] == "tie"
        # A tie has no loser, so no bust callout.
        assert "bust" not in beat

    def test_bench_below_threshold_omitted(self, recap_outline):
        a = _team("Aces", "alice", 120, top=_player(), bench=10.0)
        b = _team("Bears", "bob", 100, bench=5.0)
        beat = recap_outline.build_outline(_highlights([_matchup(a, b)]))["matchups"][0]
        assert "bench" not in beat

    def test_empty_week(self, recap_outline):
        out = recap_outline.build_outline(_highlights([]))
        assert out["matchups"] == []
        assert out["headline_angle"] == "general"


class TestIsChampionship:
    def test_none_is_false(self, recap_outline):
        assert recap_outline._is_championship(None) is False

    def test_empty_is_false(self, recap_outline):
        assert recap_outline._is_championship("") is False

    def test_finals_is_true(self, recap_outline):
        assert recap_outline._is_championship("Finals") is True

    def test_semifinals_is_false(self, recap_outline):
        assert recap_outline._is_championship("Semifinals") is False
