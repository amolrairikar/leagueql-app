"""Deterministic story outline for the weekly recap (BE-022).

``build_outline`` turns the deterministic highlights dict (``highlights.py``) into
an ordered, labeled **story plan** — no prose. It is the scaffold the LLM
(``ai_generate.py``) writes the column around: it fixes the headline angle, the
order matchups are covered in, and which beats matter, so the AI's output is
cohesive *and* consistently structured rather than a free-form ramble.

Pure function, no LLM / network / DynamoDB. Selection mirrors the snippet
composer (``generate.py``) so the outline and the deterministic fallback agree on
what the week's story is (headline group, extremes, title framing).
"""

# The only tier that earns advance / championship framing; every other non-NONE
# tier is a consolation game (pride only). Mirrors ``generate.py:_TITLE_TIER``.
_TITLE_TIER = "WINNERS_BRACKET"

# Bench points at/above which "left on the bench" is a storyline, not noise.
# Mirrors ``generate.py:_BENCH_THRESHOLD``.
_BENCH_THRESHOLD = 20.0


def _name(side: dict) -> str:
    """A team's display label: team name, falling back to the manager."""
    return side.get("team_name") or side.get("manager") or "a team"


def _is_championship(round_name) -> bool:
    """True when a playoff round name denotes the title game.

    Matches "championship"/"champ..." or a bare "final"/"finals" — not
    "semifinals". Mirrors ``generate.py:_is_championship``.
    """
    if not round_name:
        return False
    low = round_name.strip().lower()
    return "champ" in low or low in {"final", "finals"}


def _bucket(margin: float) -> str:
    """Bucket a winning margin into a qualitative label (mirrors ``generate.py``)."""
    if margin < 3:
        return "nailbiter"
    if margin < 10:
        return "close"
    if margin < 20:
        return "solid"
    if margin < 40:
        return "comfortable"
    return "blowout"


def _headline_group(matchups: list[dict]) -> str:
    """The week's headline angle (mirrors ``generate.py:_headline`` selection).

    Only true ``WINNERS_BRACKET`` games drive playoff / championship angles; a
    week of pure consolation/losers games reads as a regular week.
    """
    title_games = [
        m for m in matchups if (m.get("playoff_tier_type") or "NONE") == _TITLE_TIER
    ]
    if any(_is_championship(m.get("playoff_round")) for m in title_games):
        return "championship"
    if title_games:
        return "playoff"
    if any(not m["tied"] and m["margin"] >= 40 for m in matchups):
        return "blowout"
    return "general"


def _significance(m: dict) -> tuple:
    """Sort key (descending) ranking a matchup's narrative weight.

    Title games first (championship over other winners-bracket games), then any
    playoff game, then by decided margin (blowouts read as bigger stories). Ties
    sort last. Stable for equal keys so the order is reproducible.
    """
    tier = m.get("playoff_tier_type") or "NONE"
    is_title = tier == _TITLE_TIER
    is_champ = is_title and _is_championship(m.get("playoff_round"))
    is_playoff = tier != "NONE"
    return (
        is_champ,
        is_title,
        is_playoff,
        not m["tied"],
        m["margin"],
    )


def _matchup_beat(m: dict) -> dict:
    """One matchup's outline beat: who played, the result, and what to call out."""
    a, b = m["team_a"], m["team_b"]
    winner, loser = (a, b) if a["score"] >= b["score"] else (b, a)
    tier = m.get("playoff_tier_type") or "NONE"

    beat = {
        "winner": _name(winner),
        "loser": _name(loser),
        "winner_score": winner["score"],
        "loser_score": loser["score"],
        "margin": m["margin"],
        "tied": m["tied"],
        "result_kind": "tie" if m["tied"] else _bucket(m["margin"]),
        "is_playoff": tier != "NONE",
        "playoff_tier_type": tier,
        "playoff_round": m.get("playoff_round"),
        "is_title_game": tier == _TITLE_TIER,
        "is_championship": tier == _TITLE_TIER
        and _is_championship(m.get("playoff_round")),
        "is_consolation": tier not in (_TITLE_TIER, "NONE"),
    }

    # Standout = the higher top scorer across the two teams (the headline performer
    # for this game). None when neither side fielded a named starter.
    cands = [
        (s["top_scorer"], _name(s))
        for s in (winner, loser)
        if s.get("top_scorer") and s["top_scorer"].get("name")
    ]
    if cands:
        player, team = max(cands, key=lambda c: c[0]["points"])
        beat["standout"] = {
            "player": player["name"],
            "position": player.get("position"),
            "points": player["points"],
            "team": team,
        }

    # Optional callouts the AI may use for color: the loser's biggest bust and the
    # most points either side left on the bench (only when worth mentioning).
    bust = loser.get("biggest_bust")
    if not m["tied"] and bust and bust.get("name"):
        beat["bust"] = {
            "team": _name(loser),
            "player": bust["name"],
            "points": bust["points"],
        }
    bench_side = max(winner, loser, key=lambda s: s.get("points_on_bench", 0.0))
    if bench_side.get("points_on_bench", 0.0) >= _BENCH_THRESHOLD:
        beat["bench"] = {
            "team": _name(bench_side),
            "points": bench_side["points_on_bench"],
        }
    return beat


def build_outline(highlights: dict) -> dict:
    """Build a deterministic story plan for one week from its highlights.

    Args:
        highlights: The deterministic highlights dict (see ``compute_highlights``).

    Returns:
        A dict the recap prompt consumes:
        ``{season, week, is_playoff_week, headline_angle, week_extremes,
        matchups: [<beat>, ...], standings}`` — matchups ordered most- to
        least-significant. Empty ``matchups`` when the week has none.
    """
    matchups = highlights.get("matchups") or []
    ordered = sorted(matchups, key=_significance, reverse=True)
    return {
        "season": highlights.get("season"),
        "week": highlights.get("week"),
        "is_playoff_week": highlights.get("is_playoff_week", False),
        "headline_angle": _headline_group(matchups),
        "week_extremes": highlights.get("week_extremes") or {},
        "matchups": [_matchup_beat(m) for m in ordered],
        "standings": highlights.get("standings") or [],
    }
