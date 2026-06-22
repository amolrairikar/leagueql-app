"""Deterministic per-week highlight extraction for the AI weekly recap (BE-022).

Pure functions: given a week's ``MATCHUPS`` rows (the ``data`` list of one
``MATCHUPS#{season}#WEEK#{WW}`` item) and the season's ``WEEKLY_STANDINGS`` rows,
produce a compact, fully-numeric ``highlights`` dict. This is the guardrail for
the LLM: every number that appears in a recap originates here, never the model.

No LLM, no network, no DynamoDB — trivially unit-testable.
"""

from typing import Any


def _f(value: Any) -> float:
    """Coerce a DynamoDB number (Decimal) / str / None to float, defaulting 0.0."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _top_and_bust(starters: list[dict]) -> tuple[dict | None, dict | None]:
    """Return (top scorer, biggest bust) starters by ``points_scored``.

    ``None`` for either when there are no starters. Ties break on ``full_name`` so
    the result is deterministic.
    """
    scored = [
        {
            "name": s.get("full_name"),
            "position": s.get("fantasy_position") or s.get("position"),
            "points": round(_f(s.get("points_scored")), 2),
        }
        for s in (starters or [])
    ]
    if not scored:
        return None, None
    top = max(scored, key=lambda p: (p["points"], _name_key(p)))
    bust = min(scored, key=lambda p: (p["points"], _name_key(p)))
    return top, bust


def _name_key(player: dict) -> str:
    return (player.get("name") or "").lower()


def _bench_points(bench: list[dict]) -> float:
    """Sum bench ``points_scored`` — a simple 'left on the bench' figure."""
    return round(sum(_f(p.get("points_scored")) for p in (bench or [])), 2)


def _team_side(matchup: dict, prefix: str) -> dict:
    """Build one team's highlight side (``prefix`` = ``team_a`` / ``team_b``)."""
    top, bust = _top_and_bust(matchup.get(f"{prefix}_starters"))
    return {
        "team_name": matchup.get(f"{prefix}_team_name")
        or matchup.get(f"{prefix}_display_name"),
        "manager": matchup.get(f"{prefix}_display_name"),
        "score": round(_f(matchup.get(f"{prefix}_score")), 2),
        "top_scorer": top,
        "biggest_bust": bust,
        "points_on_bench": _bench_points(matchup.get(f"{prefix}_bench")),
    }


def _standings_for_week(weekly_standings_rows: list[dict], week: str) -> list[dict]:
    """Rank the league through ``week`` from the matching snapshot rows.

    Filters ``weekly_standings_rows`` to ``snapshot_week == week`` and returns a
    compact, ranked list (rank by wins, then points-for). Empty when the season
    has no snapshot for that week.
    """
    rows = [
        r
        for r in (weekly_standings_rows or [])
        if str(r.get("snapshot_week")) == str(week)
    ]
    rows.sort(
        key=lambda r: (
            -int(r.get("wins", 0) or 0),
            -_f(r.get("total_pf")),
            (r.get("owner_username") or "").lower(),
        )
    )
    return [
        {
            "rank": idx + 1,
            "manager": r.get("owner_username"),
            "team_name": r.get("team_name"),
            "record": r.get("record"),
            "points_for": round(_f(r.get("total_pf")), 2),
        }
        for idx, r in enumerate(rows)
    ]


def compute_highlights(
    matchup_list: list[dict],
    weekly_standings_rows: list[dict],
    season: str,
    week: str,
) -> dict:
    """Build the deterministic highlights for one week.

    Args:
        matchup_list: The ``data`` list of one ``MATCHUPS#{season}#WEEK#{WW}`` item.
        weekly_standings_rows: The ``data`` list of the season's ``WEEKLY_STANDINGS``
            item (all weeks); filtered to ``week`` internally.
        season: Season year (e.g. ``"2025"``).
        week: Week number (e.g. ``"1"``).

    Returns:
        A compact, fully-numeric dict the recap prompt consumes. ``matchups`` is a
        list of per-game highlight objects; ``week_extremes`` carries the closest /
        biggest decided margins; ``standings`` is the ranked snapshot through the
        week.
    """
    matchups: list[dict] = []
    margins: list[dict] = []
    for m in matchup_list or []:
        # Skip bye / self-matchup placeholders (no real opponent).
        if m.get("team_a_id") and m.get("team_a_id") == m.get("team_b_id"):
            continue
        side_a = _team_side(m, "team_a")
        side_b = _team_side(m, "team_b")
        tied = side_a["score"] == side_b["score"]
        if side_a["score"] >= side_b["score"]:
            winner, loser = side_a, side_b
        else:
            winner, loser = side_b, side_a
        margin = round(abs(side_a["score"] - side_b["score"]), 2)
        matchups.append(
            {
                "team_a": side_a,
                "team_b": side_b,
                "winner": None if tied else winner["manager"],
                "loser": None if tied else loser["manager"],
                "margin": margin,
                "tied": tied,
            }
        )
        if not tied:
            margins.append(
                {
                    "winner": winner["manager"],
                    "loser": loser["manager"],
                    "margin": margin,
                }
            )

    week_extremes: dict = {}
    if margins:
        week_extremes = {
            "biggest_margin": max(
                margins, key=lambda x: (x["margin"], x["winner"] or "")
            ),
            "closest_margin": min(
                margins, key=lambda x: (x["margin"], x["winner"] or "")
            ),
        }

    return {
        "season": season,
        "week": week,
        "matchups": matchups,
        "week_extremes": week_extremes,
        "standings": _standings_for_week(weekly_standings_rows, week),
    }
