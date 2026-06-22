"""Deterministic weekly recap composition from a snippet phrase bank (BE-022).

No LLM, no network. ``generate_recap`` turns the deterministic highlights dict
(``highlights.py``) into a ``{headline, body}`` "commissioner's column": one short
paragraph (2-3 sentences) per matchup, joined by blank lines. Each sentence is
drawn from ``snippets.py`` with a **per-matchup seeded RNG** keyed off that
matchup's own facts, so the same week always renders the same recap (stable on
idempotent re-fire) while different matchups and weeks read differently — and
tests are deterministic without monkeypatching.

This replaced an Amazon Bedrock LLM call; the public surface (``generate_recap``,
``RecapGenerationError``, ``MODEL_ID``) is unchanged so ``handler.py`` is agnostic
to how the prose is produced.
"""

import hashlib
import random

import snippets

# Generator/version sentinel stored in the RECAP item's ``model`` field, so a
# recap can be traced to the composer that wrote it (and force-regenerated if the
# snippet bank changes materially).
MODEL_ID = "snippet-v1"

# Bench points at/above which "you left points on the bench" is worth a callout —
# below this it's noise, not a storyline.
_BENCH_THRESHOLD = 20.0


class RecapGenerationError(Exception):
    """Raised when a week cannot be composed (e.g. no matchups).

    Composition is deterministic and effectively always succeeds, so this is a
    defensive guard; the caller leaves that week un-recapped and a later retry
    fills it. Kept for ``handler.py`` import/JOB_STATUS-failure compatibility.
    """


def _rng(*parts) -> random.Random:
    """A ``random.Random`` seeded by a stable hash of ``parts``.

    Uses ``hashlib`` (not the salted built-in ``hash``) so the seed — and thus the
    rendered recap — is identical across processes and runs.
    """
    key = "|".join(str(p) for p in parts)
    seed = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return random.Random(seed)


def _fmt(value) -> str:
    """Format a score/points/margin: drop a trailing ``.0`` but keep real decimals."""
    f = float(value)
    return str(int(f)) if f == int(f) else f"{f:g}"


def _name(side: dict) -> str:
    """A team's display label: team name, falling back to the manager."""
    return side.get("team_name") or side.get("manager") or "a team"


def _is_championship(round_name) -> bool:
    """True when a playoff round name denotes the title game.

    Matches "championship"/"champ..." or a bare "final"/"finals" — deliberately
    NOT "semifinals" (which merely contains "final").
    """
    if not round_name:
        return False
    low = round_name.strip().lower()
    return "champ" in low or low in {"final", "finals"}


def _best_scorer(*sides) -> tuple[dict, str] | None:
    """Return ``(top_scorer, team_label)`` for the higher top scorer across sides.

    ``None`` when no side fielded a named starter.
    """
    cands = [
        (s["top_scorer"], _name(s))
        for s in sides
        if s.get("top_scorer") and s["top_scorer"].get("name")
    ]
    if not cands:
        return None
    return max(cands, key=lambda c: c[0]["points"])


def _result_sentence(rng, winner, loser, margin, tied, is_playoff, round_name):
    """Compose the opening result sentence for a matchup."""
    if tied:
        tpl = rng.choice(snippets.RESULT["tie"])
        return tpl.format(
            team_a=_name(winner), team_b=_name(loser), score=_fmt(winner["score"])
        )

    ctx = {
        "winner": _name(winner),
        "loser": _name(loser),
        "winner_score": _fmt(winner["score"]),
        "loser_score": _fmt(loser["score"]),
        "margin": _fmt(margin),
        "round": round_name or "",
    }

    if is_playoff:
        if _is_championship(round_name):
            tpl = rng.choice(snippets.PLAYOFF_RESULT["championship"])
        elif round_name:
            tpl = rng.choice(snippets.PLAYOFF_RESULT["advance"])
        else:
            tpl = rng.choice(snippets.PLAYOFF_RESULT["advance_generic"])
        return tpl.format(**ctx)

    tpl = rng.choice(snippets.RESULT[_bucket(margin)])
    return tpl.format(**ctx)


def _bucket(margin: float) -> str:
    if margin < 3:
        return "nailbiter"
    if margin < 10:
        return "close"
    if margin < 20:
        return "solid"
    if margin < 40:
        return "comfortable"
    return "blowout"


def _standout_sentence(rng, winner, loser):
    """Compose the standout-performance sentence, or ``None`` if no starters."""
    best = _best_scorer(winner, loser)
    if not best:
        return None
    player, team = best
    if player.get("position"):
        tpl = rng.choice(snippets.STANDOUT_WITH_POS)
        return tpl.format(
            player=player["name"],
            points=_fmt(player["points"]),
            position=player["position"],
            team=team,
        )
    tpl = rng.choice(snippets.STANDOUT)
    return tpl.format(player=player["name"], points=_fmt(player["points"]), team=team)


def _flavor_sentence(rng, winner, loser, tied, is_playoff):
    """Pick at most one optional flavor sentence (bust / bench / trash / eliminated).

    Returns ``None`` when nothing is eligible or the RNG draws the no-flavor slot
    (so paragraphs stay a natural 2-3 sentences).
    """
    keys: list[str | None] = []
    if not tied:
        keys.append("trash")
        bust = loser.get("biggest_bust")
        if bust and bust.get("name"):
            keys.append("bust")
        if is_playoff:
            keys.append("eliminated")

    bench_side = max(winner, loser, key=lambda s: s.get("points_on_bench", 0.0))
    if bench_side.get("points_on_bench", 0.0) >= _BENCH_THRESHOLD:
        keys.append("bench")

    if not keys:
        return None
    keys.append(None)  # a chance at no third sentence, for variety
    key = rng.choice(keys)
    if key is None:
        return None

    tpl = rng.choice(snippets.FLAVOR[key])
    if key == "bust":
        bust = loser["biggest_bust"]
        return tpl.format(
            team=_name(loser), player=bust["name"], points=_fmt(bust["points"])
        )
    if key == "bench":
        return tpl.format(
            team=_name(bench_side), bench=_fmt(bench_side["points_on_bench"])
        )
    if key == "eliminated":
        return tpl.format(
            loser=_name(loser), loser_mgr=loser.get("manager") or _name(loser)
        )
    # trash
    return tpl.format(
        loser=_name(loser),
        loser_mgr=loser.get("manager") or _name(loser),
        winner=_name(winner),
    )


def _extreme_tags(highlights: dict) -> dict[int, str]:
    """Map matchup index -> "biggest"/"closest" for the week's extreme decided games.

    A matchup that is both (only one decided game all week) is tagged "biggest".
    """
    extremes = highlights.get("week_extremes") or {}
    matchups = highlights.get("matchups") or []
    tags: dict[int, str] = {}

    def _match(target, label):
        if not target:
            return
        for i, m in enumerate(matchups):
            if i in tags or m["tied"]:
                continue
            if (
                m["winner"] == target["winner"]
                and m["loser"] == target["loser"]
                and m["margin"] == target["margin"]
            ):
                tags[i] = label
                return

    _match(extremes.get("biggest_margin"), "biggest")
    _match(extremes.get("closest_margin"), "closest")
    return tags


def _matchup_paragraph(rng, m: dict, extreme_tag: str | None) -> str:
    """Compose one matchup's 2-3 sentence paragraph."""
    a, b = m["team_a"], m["team_b"]
    winner, loser = (a, b) if a["score"] >= b["score"] else (b, a)

    sentences = [
        _result_sentence(
            rng,
            winner,
            loser,
            m["margin"],
            m["tied"],
            m["is_playoff"],
            m.get("playoff_round"),
        )
    ]
    standout = _standout_sentence(rng, winner, loser)
    if standout:
        sentences.append(standout)
    flavor = _flavor_sentence(rng, winner, loser, m["tied"], m["is_playoff"])
    if flavor:
        sentences.append(flavor)
    if extreme_tag:
        sentences.append(rng.choice(snippets.WEEK_EXTREME[extreme_tag]))
    return " ".join(sentences)


def _headline(rng, highlights: dict) -> str:
    matchups = highlights.get("matchups") or []
    if any(
        m["is_playoff"] and _is_championship(m.get("playoff_round")) for m in matchups
    ):
        group = "championship"
    elif highlights.get("is_playoff_week"):
        group = "playoff"
    elif any(not m["tied"] and m["margin"] >= 40 for m in matchups):
        group = "blowout"
    else:
        group = "general"
    return rng.choice(snippets.HEADLINES[group])


def generate_recap(highlights: dict, season: str, week: str) -> dict:
    """Compose a ``{headline, body}`` recap for one week from its highlights.

    Args:
        highlights: The deterministic highlights dict (see ``compute_highlights``).
        season: Season year (seeds the RNG; keeps output stable per week).
        week: Week number (seeds the RNG).

    Returns:
        ``{"headline": str, "body": str}``.

    Raises:
        RecapGenerationError: The week has no matchups to write about.
    """
    matchups = highlights.get("matchups") or []
    if not matchups:
        raise RecapGenerationError(f"No matchups to recap for {season} week {week}")

    tags = _extreme_tags(highlights)
    paragraphs = []
    for i, m in enumerate(matchups):
        a, b = m["team_a"], m["team_b"]
        rng = _rng(
            season,
            week,
            i,
            a.get("manager"),
            b.get("manager"),
            a.get("score"),
            b.get("score"),
            m["margin"],
        )
        paragraphs.append(_matchup_paragraph(rng, m, tags.get(i)))

    headline = _headline(_rng(season, week, "headline"), highlights)
    return {"headline": headline.strip(), "body": "\n\n".join(paragraphs).strip()}
