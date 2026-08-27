"""
seed_demo_data.py

Generates frontend/src/lib/demo-data.json — the static demo dataset
served by the LeagueQL frontend when running in demo mode.

The data is produced deterministically (seed=42), so re-running this
script always yields the same output.

Usage:
    pipenv run python scripts/utility_scripts/seed_demo_data.py
    pipenv run python scripts/utility_scripts/seed_demo_data.py --dry-run
    pipenv run python scripts/utility_scripts/seed_demo_data.py --out path/to/output.json
"""

import argparse
import datetime
import json
import logging
import pathlib
import random
from decimal import Decimal
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

SEED = 42
DEMO_LEAGUE_ID = "999999999"
DEMO_SLEEPER_LEAGUE_ID = "888888888"
DEMO_CANONICAL_ID = "demo-league-canonical"
DEMO_LEAGUE_NAME = "Demo Fantasy League"
PLATFORM = "ESPN"
SLEEPER_PLATFORM = "SLEEPER"
SEASONS = ["2022", "2023", "2024"]
SLEEPER_SEASONS = ["2025"]
ONBOARDED_AT = "2024-09-01T00:00:00"
MIGRATED_AT = "2025-09-01T00:00:00"
N_REG_WEEKS = 15
N_TEAMS = 10
N_PLAYOFF_TEAMS = 4
N_BYE_TEAMS = 0
DRAFT_ROUNDS = 14

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = _REPO_ROOT / "frontend" / "src" / "lib" / "demo-data.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Owners ────────────────────────────────────────────────────────────────────

BASE_OWNERS = [
    {
        "id": "1",
        "owner_id": "owner_01",
        "username": "alex_t",
        "team_name": "Gridiron Gurus",
    },
    {
        "id": "2",
        "owner_id": "owner_02",
        "username": "jordan_l",
        "team_name": "End Zone Warriors",
    },
    {
        "id": "3",
        "owner_id": "owner_03",
        "username": "morgan_d",
        "team_name": "Blitz Brigade",
    },
    {
        "id": "4",
        "owner_id": "owner_04",
        "username": "taylor_w",
        "team_name": "Touchdown Tycoons",
    },
    {
        "id": "5",
        "owner_id": "owner_05",
        "username": "sam_w",
        "team_name": "The Avengers",
    },
    {
        "id": "6",
        "owner_id": "owner_06",
        "username": "chris_j",
        "team_name": "Red Zone Raiders",
    },
    {
        "id": "7",
        "owner_id": "owner_07",
        "username": "riley_b",
        "team_name": "Fourth Quarter",
    },
    {
        "id": "8",
        "owner_id": "owner_08",
        "username": "casey_g",
        "team_name": "Rushing Renegades",
    },
    {
        "id": "9",
        "owner_id": "owner_09",
        "username": "drew_m",
        "team_name": "Deep Routes",
    },
    {
        "id": "10",
        "owner_id": "owner_10",
        "username": "jamie_a",
        "team_name": "Special Teams FC",
    },
]

SEASON_OVERRIDES: dict[str, dict[str, dict]] = {
    "2023": {
        "4": {
            "owner_id": "owner_11",
            "username": "quinn_r",
            "team_name": "Fantasy Kings",
        }
    },
    "2024": {
        "2": {
            "owner_id": "owner_12",
            "username": "blake_t",
            "team_name": "Stat Hunters",
        },
        "4": {
            "owner_id": "owner_11",
            "username": "quinn_r",
            "team_name": "Fantasy Kings",
        },
    },
}


def get_owners(season: str) -> list[dict]:
    overrides = SEASON_OVERRIDES.get(season, {})
    owners = []
    for o in BASE_OWNERS:
        owner = dict(o)
        if o["id"] in overrides:
            owner.update(overrides[o["id"]])
        owners.append(owner)
    return owners


def get_sleeper_owners() -> list[dict]:
    """2025 Sleeper owners: mirror the 2024 ESPN roster with sl_ prefixed owner IDs."""
    return [{**o, "owner_id": f"sl_{o['owner_id']}"} for o in get_owners("2024")]


def get_migration_mapping() -> list[dict]:
    """Map each 2024 ESPN owner_id to its 2025 Sleeper counterpart."""
    return [
        {
            "current_platform_owner_id": o["owner_id"],
            "new_platform_owner_id": f"sl_{o['owner_id']}",
            "display_name": o["username"],
        }
        for o in get_owners("2024")
    ]


# ── Player pool ───────────────────────────────────────────────────────────────

_pid = 1001


def _p(name: str, avg: float, std: float) -> dict:
    global _pid
    player = {"player_id": _pid, "full_name": name, "avg": avg, "std": std}
    _pid += 1
    return player


PLAYER_POOL: dict[str, list[dict]] = {
    "QB": [
        _p("Patrick Mahomes", 28.5, 7.0),
        _p("Josh Allen", 27.2, 8.5),
        _p("Jalen Hurts", 26.8, 7.5),
        _p("Lamar Jackson", 25.5, 8.0),
        _p("Joe Burrow", 23.5, 7.0),
        _p("Justin Herbert", 22.0, 6.5),
        _p("Dak Prescott", 21.5, 6.5),
        _p("Tua Tagovailoa", 20.8, 6.0),
        _p("Trevor Lawrence", 20.2, 6.5),
        _p("Kirk Cousins", 19.8, 6.0),
        _p("Geno Smith", 18.5, 5.5),
        _p("Justin Fields", 22.0, 9.0),
        _p("Kyler Murray", 21.5, 7.0),
        _p("Derek Carr", 17.5, 5.5),
        _p("Ryan Tannehill", 16.5, 5.5),
        _p("Tom Brady", 18.0, 5.5),
    ],
    "RB": [
        _p("Christian McCaffrey", 24.5, 6.0),
        _p("Austin Ekeler", 20.5, 7.0),
        _p("Dalvin Cook", 16.0, 6.5),
        _p("Derrick Henry", 17.5, 8.0),
        _p("Nick Chubb", 16.5, 7.0),
        _p("Josh Jacobs", 18.0, 7.0),
        _p("Tony Pollard", 15.5, 6.5),
        _p("Breece Hall", 17.0, 7.5),
        _p("Jonathan Taylor", 16.0, 8.0),
        _p("Najee Harris", 13.5, 5.5),
        _p("D'Andre Swift", 14.5, 6.5),
        _p("Miles Sanders", 12.5, 5.5),
        _p("Travis Etienne", 15.0, 6.5),
        _p("Rhamondre Stevenson", 14.0, 6.5),
        _p("Dameon Pierce", 13.0, 6.0),
        _p("Raheem Mostert", 12.0, 6.0),
        _p("Isiah Pacheco", 13.0, 6.5),
        _p("David Montgomery", 12.5, 5.5),
        _p("Alvin Kamara", 14.0, 7.0),
        _p("Saquon Barkley", 17.0, 8.0),
        _p("Aaron Jones", 13.5, 6.5),
        _p("Kareem Hunt", 11.0, 5.5),
        _p("Leonard Fournette", 12.0, 6.0),
        _p("Cordarrelle Patterson", 11.5, 6.0),
        _p("Ezekiel Elliott", 12.0, 6.0),
        _p("James Conner", 13.0, 6.5),
        _p("Clyde Edwards-Helaire", 10.5, 5.5),
        _p("Chase Edmonds", 9.5, 5.0),
        _p("Jamaal Williams", 11.5, 5.5),
        _p("Antonio Gibson", 10.5, 5.5),
        _p("Elijah Mitchell", 11.0, 6.0),
        _p("Rachaad White", 12.0, 5.5),
        _p("Devin Singletary", 10.5, 5.0),
        _p("J.K. Dobbins", 12.0, 7.0),
        _p("Javonte Williams", 11.5, 6.0),
        _p("Kenneth Walker III", 14.5, 6.5),
        _p("Cam Akers", 11.0, 6.0),
        _p("De'Von Achane", 15.0, 8.0),
        _p("Zach Charbonnet", 10.5, 5.5),
        _p("Chuba Hubbard", 10.0, 5.5),
        _p("AJ Dillon", 10.0, 5.5),
        _p("Tyler Allgeier", 11.0, 5.5),
        _p("Jaylen Warren", 9.5, 5.0),
        _p("Tony Jones Jr.", 8.0, 4.5),
        _p("Samaje Perine", 8.5, 4.5),
    ],
    "WR": [
        _p("Justin Jefferson", 21.5, 7.5),
        _p("Tyreek Hill", 20.5, 8.0),
        _p("Stefon Diggs", 17.5, 7.0),
        _p("Davante Adams", 18.5, 7.5),
        _p("Cooper Kupp", 19.0, 8.0),
        _p("CeeDee Lamb", 20.0, 7.5),
        _p("Ja'Marr Chase", 18.5, 8.5),
        _p("DeVonta Smith", 15.5, 6.5),
        _p("A.J. Brown", 18.0, 7.5),
        _p("Tee Higgins", 15.0, 7.0),
        _p("DK Metcalf", 14.5, 7.0),
        _p("Amari Cooper", 14.0, 6.5),
        _p("Keenan Allen", 14.5, 6.0),
        _p("Jaylen Waddle", 14.5, 6.5),
        _p("Christian Kirk", 13.5, 6.5),
        _p("Tyler Lockett", 13.5, 6.5),
        _p("Deebo Samuel", 14.5, 8.0),
        _p("Terry McLaurin", 13.0, 6.5),
        _p("Brandon Aiyuk", 15.0, 7.0),
        _p("Chris Godwin", 13.0, 6.5),
        _p("Mike Evans", 14.5, 7.5),
        _p("Amon-Ra St. Brown", 16.0, 6.0),
        _p("Diontae Johnson", 12.0, 6.0),
        _p("Courtland Sutton", 12.5, 6.5),
        _p("Michael Pittman Jr.", 13.0, 6.0),
        _p("DeVante Parker", 11.5, 6.5),
        _p("Nelson Agholor", 10.0, 5.5),
        _p("Marquez Valdes-Scantling", 11.0, 7.0),
        _p("Gabe Davis", 12.0, 7.5),
        _p("Donovan Peoples-Jones", 11.0, 6.5),
        _p("Calvin Ridley", 13.0, 6.5),
        _p("Drake London", 12.5, 6.0),
        _p("Treylon Burks", 10.5, 5.5),
        _p("Wan'Dale Robinson", 10.0, 5.5),
        _p("Elijah Moore", 9.5, 5.5),
        _p("Kadarius Toney", 10.5, 7.0),
        _p("Rashid Shaheed", 12.0, 7.5),
        _p("Jaxon Smith-Njigba", 12.5, 6.0),
        _p("Jordan Addison", 13.0, 6.5),
        _p("Zay Flowers", 13.5, 7.0),
        _p("Puka Nacua", 16.0, 7.0),
        _p("Odell Beckham Jr.", 11.5, 6.5),
        _p("Emmanuel Sanders", 9.0, 5.0),
        _p("Darius Slayton", 10.5, 6.0),
        _p("Allen Lazard", 9.5, 5.5),
        _p("Robert Woods", 9.0, 5.0),
        _p("Kendrick Bourne", 9.5, 5.5),
        _p("Braxton Berrios", 8.5, 5.0),
        _p("Trent Sherfield", 8.0, 4.5),
        _p("Parris Campbell", 9.0, 5.5),
    ],
    "TE": [
        _p("Travis Kelce", 20.0, 6.5),
        _p("Mark Andrews", 16.5, 7.0),
        _p("Tyler Higbee", 11.0, 5.5),
        _p("Dalton Schultz", 10.5, 5.5),
        _p("T.J. Hockenson", 13.5, 6.0),
        _p("Dallas Goedert", 12.5, 6.0),
        _p("Pat Freiermuth", 10.0, 5.0),
        _p("Cole Kmet", 10.5, 5.0),
        _p("Kyle Pitts", 11.0, 6.5),
        _p("Evan Engram", 12.0, 6.0),
        _p("David Njoku", 11.5, 5.5),
        _p("Gerald Everett", 9.5, 5.0),
        _p("Hayden Hurst", 9.0, 5.0),
        _p("Zach Ertz", 10.0, 5.5),
        _p("Logan Thomas", 8.5, 4.5),
        _p("Robert Tonyan", 8.0, 4.5),
    ],
    "K": [
        _p("Justin Tucker", 10.5, 3.0),
        _p("Evan McPherson", 10.0, 3.5),
        _p("Tyler Bass", 9.5, 3.5),
        _p("Daniel Carlson", 9.5, 3.0),
        _p("Harrison Butker", 10.0, 3.0),
        _p("Matt Gay", 9.0, 3.5),
        _p("Jake Elliott", 9.0, 3.0),
        _p("Nick Folk", 9.0, 3.0),
        _p("Jason Sanders", 8.5, 3.0),
        _p("Ryan Succop", 8.5, 3.0),
        _p("Robbie Gould", 8.5, 3.0),
        _p("Younghoe Koo", 9.0, 3.5),
        _p("Mason Crosby", 8.5, 3.5),
        _p("Chris Boswell", 9.0, 3.5),
    ],
    "D/ST": [
        _p("San Francisco 49ers", 11.5, 5.0),
        _p("Buffalo Bills", 11.0, 5.0),
        _p("Dallas Cowboys", 10.5, 5.0),
        _p("Philadelphia Eagles", 10.0, 5.0),
        _p("New England Patriots", 9.5, 5.0),
        _p("Baltimore Ravens", 10.5, 5.0),
        _p("Minnesota Vikings", 9.0, 4.5),
        _p("Pittsburgh Steelers", 10.0, 5.0),
        _p("Tampa Bay Buccaneers", 9.5, 5.0),
        _p("Los Angeles Rams", 9.5, 5.0),
        _p("Cincinnati Bengals", 9.5, 5.0),
        _p("Kansas City Chiefs", 9.0, 4.5),
        _p("New York Jets", 9.0, 4.5),
        _p("Green Bay Packers", 8.5, 4.5),
    ],
}

ALL_PLAYERS: dict[int, dict] = {
    p["player_id"]: p for players in PLAYER_POOL.values() for p in players
}

PLAYER_TO_POS: dict[int, str] = {
    p["player_id"]: pos for pos, players in PLAYER_POOL.items() for p in players
}


# ── Utilities ─────────────────────────────────────────────────────────────────


def sanitize_value(val: Any) -> Any:
    if isinstance(val, float):
        return Decimal(str(round(val, 2)))
    if isinstance(val, list):
        return [sanitize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: sanitize_value(v) for k, v in val.items()}
    return val


def fmt_score(score: float) -> float:
    return round(score, 2)


def fmt_win_pct(pct: float) -> float:
    """Format win percentage to 3 decimal places for precision."""
    return round(pct, 3)


# ── Draft ─────────────────────────────────────────────────────────────────────


# Synthetic auction pricing. Bids are derived from a player's preseason
# projection (their generating `avg`) above a positional baseline, so the market
# price reflects expectations while realized points may differ — producing genuine
# auction steals and busts. Used to build the separate DRAFT_AUCTION#<season>
# demo dataset.
AUCTION_POS_BASELINE = {"QB": 17.0, "RB": 10.0, "WR": 10.0, "TE": 9.0}
AUCTION_POS_SCALE = {"QB": 3.0, "RB": 3.0, "WR": 3.0, "TE": 3.0}


def _auction_bid(pos: str, avg: float, rng: random.Random) -> int:
    """Synthetic auction bid (in dollars) for a player.

    Skill players are priced off their projection above a positional baseline,
    with small jitter so price order isn't a perfect echo of projection. Kickers
    and defenses sit at near-minimum bids, as in real auctions.
    """
    if pos in ("K", "D/ST"):
        return max(1, round(rng.uniform(1.0, 3.0)))
    baseline = AUCTION_POS_BASELINE.get(pos, 10.0)
    scale = AUCTION_POS_SCALE.get(pos, 3.0)
    return max(1, round((avg - baseline) * scale + rng.gauss(0.0, 3.0)))


def _rank_desc_with_ties(values: dict[Any, float]) -> dict[Any, int]:
    """Rank keys by value descending using SQL RANK() semantics: ties share a
    rank and the next distinct value skips ranks accordingly."""
    ranks: dict[Any, int] = {}
    prev_val: float | None = None
    prev_rank = 0
    for i, (key, val) in enumerate(
        sorted(values.items(), key=lambda kv: -kv[1]), start=1
    ):
        if val != prev_val:
            prev_rank, prev_val = i, val
        ranks[key] = prev_rank
    return ranks


def build_auction_draft_rows(snake_rows: list[dict], rng: random.Random) -> list[dict]:
    """Build auction-format draft rows from the snake draft rows.

    Reuses the same player→team assignments and realized point totals (so the
    rest of the demo league stays coherent), but re-expresses the draft as an
    auction: each player gets a bid, drafted_position_rank is ranked by bid
    within position, and is_auction is set. Bids reflect projections while ranks
    elsewhere reflect realized points, so the rank delta surfaces real value.
    """
    bids: dict[int, int] = {}
    pos_bids: dict[str, dict[int, float]] = {}
    for i, row in enumerate(snake_rows):
        pos = row["position"]
        avg = ALL_PLAYERS[int(row["player_id"])]["avg"]
        bid = _auction_bid(pos, avg, rng)
        bids[i] = bid
        pos_bids.setdefault(pos, {})[i] = float(bid)

    drafted_rank: dict[int, int] = {}
    for entries in pos_bids.values():
        drafted_rank.update(_rank_desc_with_ties(entries))

    auction_rows: list[dict] = []
    for i, row in enumerate(snake_rows):
        dr = drafted_rank[i]
        auction_rows.append(
            {
                **row,
                "bid_amount": bids[i],
                "is_auction": True,
                "drafted_position_rank": dr,
                "draft_rank_delta": dr - row["actual_position_rank"],
            }
        )
    return auction_rows


def _draft_value(pos: str, player: dict, pos_counts: dict[str, int]) -> float:
    """Returns relative draft value for a skill-round pick (rounds 1-12)."""
    avg = player["avg"]
    count = pos_counts.get(pos, 0)
    if pos == "QB":
        return avg if count == 0 else 0.0
    if pos in ("RB", "WR"):
        return avg
    if pos == "TE":
        return avg * 0.9 if count == 0 else 0.0
    return 0.0  # K and D/ST handled separately


def build_draft(
    owners: list[dict],
    rng: random.Random,
    prev_standings: list[dict] | None,
) -> tuple[list[dict], dict[str, list[tuple[str, dict]]]]:
    """
    Snake draft. Rounds 1-12: skill players (QB/RB/WR/TE).
    Round 13: K. Round 14: D/ST.

    Returns (picks, rosters) where rosters maps team_id to list of (pos, player).
    """
    # Draft order: worst-to-best from prior season; random for first season
    if prev_standings:
        order = [
            s["team_id"]
            for s in sorted(prev_standings, key=lambda s: (s["wins"], s["total_pf"]))
        ]
    else:
        order = [o["id"] for o in owners]
        rng.shuffle(order)

    # Available players by position
    available: dict[str, list[dict]] = {
        pos: list(players) for pos, players in PLAYER_POOL.items()
    }

    rosters: dict[str, list[tuple[str, dict]]] = {o["id"]: [] for o in owners}
    picks: list[dict] = []
    overall = 1

    for round_num in range(1, DRAFT_ROUNDS + 1):
        round_order = order if round_num % 2 == 1 else list(reversed(order))

        for round_pick, team_id in enumerate(round_order, start=1):
            roster = rosters[team_id]
            pos_counts: dict[str, int] = {}
            for p_pos, _ in roster:
                pos_counts[p_pos] = pos_counts.get(p_pos, 0) + 1

            if round_num == DRAFT_ROUNDS - 1:  # round 13: K
                pos = "K"
                player = available[pos].pop(0)
            elif round_num == DRAFT_ROUNDS:  # round 14: D/ST
                pos = "D/ST"
                player = available[pos].pop(0)
            else:
                # Pick best available skill player
                best_pos, best_player, best_val = None, None, -1.0
                for p in ("QB", "RB", "WR", "TE"):
                    if not available[p]:
                        continue
                    candidate = available[p][0]
                    val = _draft_value(p, candidate, pos_counts)
                    if val > best_val:
                        best_val, best_pos, best_player = val, p, candidate
                pos = best_pos
                player = best_player
                available[pos].remove(player)

            rosters[team_id].append((pos, player))
            owner = next(o for o in owners if o["id"] == team_id)
            picks.append(
                {
                    "team_id": team_id,
                    "owner_id": owner["owner_id"],
                    "owner_username": owner["username"],
                    "team_name": owner["team_name"],
                    "round": round_num,
                    "round_pick_number": round_pick,
                    "overall_pick_number": overall,
                    "player_id": player["player_id"],
                    "player_name": player["full_name"],
                    "position": pos,
                }
            )
            overall += 1

    return picks, rosters


# ── Schedule ──────────────────────────────────────────────────────────────────


def generate_schedule(n_teams: int, n_weeks: int) -> list[list[tuple[str, str]]]:
    """
    Round-robin schedule. Returns list of n_weeks rounds, each round a list of
    (team_index_a, team_index_b) pairs (0-indexed integers).
    """
    teams = list(range(n_teams))
    base_rounds = []
    for _ in range(n_teams - 1):
        pairs = [(teams[i], teams[n_teams - 1 - i]) for i in range(n_teams // 2)]
        base_rounds.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    schedule = []
    for week in range(n_weeks):
        schedule.append(base_rounds[week % len(base_rounds)])
    return schedule


# ── Weekly score generation ───────────────────────────────────────────────────


def gen_weekly_scores(
    rosters: dict[str, list[tuple[str, dict]]],
    n_weeks: int,
    rng: random.Random,
) -> dict[str, dict[int, dict[int, float]]]:
    """
    Returns scores[team_id][week][player_id] = score.
    Weeks are 1-indexed (1..n_weeks).
    """
    scores: dict[str, dict[int, dict[int, float]]] = {}
    for team_id, roster in rosters.items():
        scores[team_id] = {}
        for week in range(1, n_weeks + 1):
            scores[team_id][week] = {}
            for pos, player in roster:
                raw = rng.gauss(player["avg"], player["std"])
                scores[team_id][week][player["player_id"]] = fmt_score(max(0.0, raw))
    return scores


def resolve_lineup(
    roster: list[tuple[str, dict]],
    week_scores: dict[int, float],
) -> tuple[list[dict], list[dict]]:
    """
    Determine optimal starting lineup and bench for one team one week.
    Slots: 1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX (RB/WR/TE), 1 K, 1 D/ST.
    Returns (starters, bench), each a list of PlayerStat dicts.
    """
    by_pos: dict[str, list[tuple[int, str, float]]] = {}  # pos → [(pid, name, score)]
    for pos, player in roster:
        pid = player["player_id"]
        entry = (pid, player["full_name"], week_scores[pid])
        by_pos.setdefault(pos, []).append(entry)

    for entries in by_pos.values():
        entries.sort(key=lambda x: -x[2])

    used_pids: set[int] = set()
    starters: list[dict] = []

    def take(pos: str, fantasy_pos: str) -> bool:
        for pid, name, score in by_pos.get(pos, []):
            if pid not in used_pids:
                starters.append(
                    {
                        "player_id": pid,
                        "full_name": name,
                        "points_scored": score,
                        "position": pos,
                        "fantasy_position": fantasy_pos,
                    }
                )
                used_pids.add(pid)
                return True
        return False

    take("QB", "QB")
    take("RB", "RB")
    take("RB", "RB")
    take("WR", "WR")
    take("WR", "WR")
    take("TE", "TE")
    take("K", "K")
    take("D/ST", "D/ST")

    # FLEX: best unused RB/WR/TE
    flex_candidates = [
        (pid, name, score, pos)
        for pos in ("RB", "WR", "TE")
        for pid, name, score in by_pos.get(pos, [])
        if pid not in used_pids
    ]
    if flex_candidates:
        flex_candidates.sort(key=lambda x: -x[2])
        pid, name, score, pos = flex_candidates[0]
        starters.append(
            {
                "player_id": pid,
                "full_name": name,
                "points_scored": score,
                "position": pos,
                "fantasy_position": "FLEX",
            }
        )
        used_pids.add(pid)

    # Bench: remaining
    bench: list[dict] = []
    for pos, player in roster:
        pid = player["player_id"]
        if pid not in used_pids:
            bench.append(
                {
                    "player_id": pid,
                    "full_name": player["full_name"],
                    "points_scored": week_scores[pid],
                    "position": pos,
                    "fantasy_position": pos,
                }
            )

    return starters, bench


# ── Season simulation ─────────────────────────────────────────────────────────


def simulate_season(
    owners: list[dict],
    rosters: dict[str, list[tuple[str, dict]]],
    all_scores: dict[str, dict[int, dict[int, float]]],
    rng: random.Random,
) -> dict:
    """
    Run regular season (weeks 1..N_REG_WEEKS), determine playoff seeds, run playoffs.
    Returns a big dict with all matchup/standings data needed to build DDB items.
    """
    owner_by_id = {o["id"]: o for o in owners}
    team_ids = [o["id"] for o in owners]

    # Regular season schedule (team-index based → convert to team_ids)
    schedule_idx = generate_schedule(N_TEAMS, N_REG_WEEKS)
    reg_matchups: list[list[dict]] = []

    # Cumulative stats per team
    wins = {t: 0 for t in team_ids}
    losses = {t: 0 for t in team_ids}
    ties = {t: 0 for t in team_ids}
    total_pf = {t: 0.0 for t in team_ids}
    total_pa = {t: 0.0 for t in team_ids}
    vs_league_wins = {t: 0 for t in team_ids}
    vs_league_losses = {t: 0 for t in team_ids}

    weekly_snapshots: list[dict] = []  # for WEEKLY_STANDINGS

    for week_idx, pairs in enumerate(schedule_idx):
        week = week_idx + 1  # 1-indexed
        week_scores_by_team: dict[str, float] = {}

        week_matchups: list[dict] = []
        for idx_a, idx_b in pairs:
            tid_a = team_ids[idx_a]
            tid_b = team_ids[idx_b]
            starters_a, bench_a = resolve_lineup(
                rosters[tid_a], all_scores[tid_a][week]
            )
            starters_b, bench_b = resolve_lineup(
                rosters[tid_b], all_scores[tid_b][week]
            )
            score_a = fmt_score(sum(p["points_scored"] for p in starters_a))
            score_b = fmt_score(sum(p["points_scored"] for p in starters_b))
            week_scores_by_team[tid_a] = score_a
            week_scores_by_team[tid_b] = score_b
            winner = tid_a if score_a >= score_b else tid_b
            loser = tid_b if score_a >= score_b else tid_a
            week_matchups.append(
                {
                    "team_a_id": tid_a,
                    "team_a_display_name": owner_by_id[tid_a]["username"],
                    "team_a_team_name": owner_by_id[tid_a]["team_name"],
                    "team_a_team_logo": None,
                    "team_a_score": score_a,
                    "team_a_starters": starters_a,
                    "team_a_bench": bench_a,
                    "team_a_primary_owner_id": owner_by_id[tid_a]["owner_id"],
                    "team_a_secondary_owner_id": None,
                    "team_b_id": tid_b,
                    "team_b_display_name": owner_by_id[tid_b]["username"],
                    "team_b_team_name": owner_by_id[tid_b]["team_name"],
                    "team_b_team_logo": None,
                    "team_b_score": score_b,
                    "team_b_starters": starters_b,
                    "team_b_bench": bench_b,
                    "team_b_primary_owner_id": owner_by_id[tid_b]["owner_id"],
                    "team_b_secondary_owner_id": None,
                    "playoff_tier_type": "NONE",
                    "playoff_round": None,
                    "winner": winner,
                    "loser": loser,
                    "week": str(week),
                    "season": None,  # filled in by caller
                }
            )
            if score_a > score_b:
                wins[tid_a] += 1
                losses[tid_b] += 1
            else:
                wins[tid_b] += 1
                losses[tid_a] += 1
            total_pf[tid_a] += score_a
            total_pa[tid_a] += score_b
            total_pf[tid_b] += score_b
            total_pa[tid_b] += score_a

        # vs_league stats for this week
        all_team_scores = list(week_scores_by_team.items())
        all_team_scores.sort(key=lambda x: -x[1])
        for rank, (tid, _) in enumerate(all_team_scores):
            vs_league_wins[tid] += N_TEAMS - 1 - rank
            vs_league_losses[tid] += rank

        reg_matchups.append(week_matchups)

        # Weekly snapshot after this week
        for t in team_ids:
            gp = wins[t] + losses[t] + ties[t]
            weekly_snapshots.append(
                {
                    "snapshot_week": str(week),
                    "team_id": t,
                    "owner_id": owner_by_id[t]["owner_id"],
                    "owner_username": owner_by_id[t]["username"],
                    "games_played": gp,
                    "wins": wins[t],
                    "losses": losses[t],
                    "ties": ties[t],
                    "record": f"{wins[t]}-{losses[t]}-{ties[t]}",
                    "win_pct": fmt_win_pct(wins[t] / gp) if gp else 0.0,
                    "total_vs_league_wins": vs_league_wins[t],
                    "total_vs_league_losses": vs_league_losses[t],
                    "win_pct_vs_league": fmt_win_pct(
                        vs_league_wins[t] / (vs_league_wins[t] + vs_league_losses[t])
                        if (vs_league_wins[t] + vs_league_losses[t]) > 0
                        else 0.0
                    ),
                    "total_pf": fmt_score(total_pf[t]),
                    "total_pa": fmt_score(total_pa[t]),
                    "avg_pf": fmt_score(total_pf[t] / gp) if gp else 0.0,
                    "avg_pa": fmt_score(total_pa[t] / gp) if gp else 0.0,
                }
            )

    # Determine playoff seeds (top 4 by wins, tiebreak: total PF)
    sorted_teams = sorted(team_ids, key=lambda t: (-wins[t], -total_pf[t]))
    playoff_seeds = sorted_teams[:N_PLAYOFF_TEAMS]  # [seed1, seed2, ...]
    consolation_teams = sorted_teams[N_PLAYOFF_TEAMS:]

    # ── Playoffs ──────────────────────────────────────────────────────────────
    # All 4 seeds play in week 16 (Semifinals); no wildcard round
    s1, s2, s3, s4 = (
        playoff_seeds[0],
        playoff_seeds[1],
        playoff_seeds[2],
        playoff_seeds[3],
    )

    def playoff_matchup(
        tid_a: str,
        tid_b: str,
        week: int,
        tier: str,
        playoff_round: str | None,
    ) -> dict:
        starters_a, bench_a = resolve_lineup(rosters[tid_a], all_scores[tid_a][week])
        starters_b, bench_b = resolve_lineup(rosters[tid_b], all_scores[tid_b][week])
        score_a = fmt_score(sum(p["points_scored"] for p in starters_a))
        score_b = fmt_score(sum(p["points_scored"] for p in starters_b))
        winner = tid_a if score_a >= score_b else tid_b
        loser = tid_b if score_a >= score_b else tid_a
        return {
            "team_a_id": tid_a,
            "team_a_display_name": owner_by_id[tid_a]["username"],
            "team_a_team_name": owner_by_id[tid_a]["team_name"],
            "team_a_team_logo": None,
            "team_a_score": score_a,
            "team_a_starters": starters_a,
            "team_a_bench": bench_a,
            "team_a_primary_owner_id": owner_by_id[tid_a]["owner_id"],
            "team_a_secondary_owner_id": None,
            "team_b_id": tid_b,
            "team_b_display_name": owner_by_id[tid_b]["username"],
            "team_b_team_name": owner_by_id[tid_b]["team_name"],
            "team_b_team_logo": None,
            "team_b_score": score_b,
            "team_b_starters": starters_b,
            "team_b_bench": bench_b,
            "team_b_primary_owner_id": owner_by_id[tid_b]["owner_id"],
            "team_b_secondary_owner_id": None,
            "playoff_tier_type": tier,
            "playoff_round": playoff_round,
            "winner": winner,
            "loser": loser,
            "week": str(week),
            "season": None,
        }

    # Playoffs run weeks 16-17 (a 2-week, 4-team format); week 15 is the final
    # regular-season week, so there are no week-15 playoff games.

    # Week 16 — Semifinals: 1 vs 4, 2 vs 3
    m1 = playoff_matchup(s1, s4, 16, "WINNERS_BRACKET", "Semifinals")
    m2 = playoff_matchup(s2, s3, 16, "WINNERS_BRACKET", "Semifinals")

    # Losers bracket (consolation) for the next 4 seeds — determines places 5-8.
    l1, l2, l3, l4 = (
        consolation_teams[0],
        consolation_teams[1],
        consolation_teams[2],
        consolation_teams[3],
    )
    lm1 = playoff_matchup(l1, l4, 16, "LOSERS_BRACKET", "Losers Bracket")
    lm2 = playoff_matchup(l2, l3, 16, "LOSERS_BRACKET", "Losers Bracket")
    week16_matchups = [m1, m2, lm1, lm2]

    # Week 17 — Championship
    sf1_winner, sf1_loser = m1["winner"], m1["loser"]
    sf2_winner, sf2_loser = m2["winner"], m2["loser"]
    m3 = playoff_matchup(sf1_winner, sf2_winner, 17, "WINNERS_BRACKET", "Finals")
    # 3rd-place game between the semifinal losers — a winners consolation game.
    m4 = playoff_matchup(
        sf1_loser, sf2_loser, 17, "WINNERS_CONSOLATION_LADDER", "Winners Consolation"
    )
    # Losers bracket finals — 5th-place game (winners) and 7th-place game (losers).
    lm3 = playoff_matchup(
        lm1["winner"], lm2["winner"], 17, "LOSERS_BRACKET", "Losers Bracket"
    )
    lm4 = playoff_matchup(
        lm1["loser"], lm2["loser"], 17, "LOSERS_BRACKET", "Losers Bracket"
    )
    week17_matchups = [m3, m4, lm3, lm4]

    champion = m3["winner"]

    # ── Final rankings ────────────────────────────────────────────────────────
    final_rank: dict[str, int] = {}
    final_rank[m3["winner"]] = 1
    final_rank[m3["loser"]] = 2
    final_rank[m4["winner"]] = 3  # 3rd-place game winner
    final_rank[m4["loser"]] = 4
    final_rank[lm3["winner"]] = 5  # 5th-place game winner
    final_rank[lm3["loser"]] = 6
    final_rank[lm4["winner"]] = 7  # 7th-place game winner
    final_rank[lm4["loser"]] = 8
    final_rank[consolation_teams[4]] = 9
    final_rank[consolation_teams[5]] = 10

    # ── STANDINGS data ────────────────────────────────────────────────────────
    standings_data: list[dict] = []
    for t in team_ids:
        gp = wins[t] + losses[t]
        vlw = vs_league_wins[t]
        vll = vs_league_losses[t]
        standings_data.append(
            {
                "team_id": t,
                "owner_id": owner_by_id[t]["owner_id"],
                "team_name": owner_by_id[t]["team_name"],
                "team_logo": None,
                "owner_username": owner_by_id[t]["username"],
                "final_rank": final_rank[t],
                "games_played": gp,
                "wins": wins[t],
                "losses": losses[t],
                "ties": 0,
                "record": f"{wins[t]}-{losses[t]}-0",
                "win_pct": fmt_win_pct(wins[t] / gp) if gp else 0.0,
                "total_vs_league_wins": vlw,
                "total_vs_league_losses": vll,
                "win_pct_vs_league": fmt_win_pct(vlw / (vlw + vll))
                if (vlw + vll) > 0
                else 0.0,
                "total_pf": fmt_score(total_pf[t]),
                "total_pa": fmt_score(total_pa[t]),
                "avg_pf": fmt_score(total_pf[t] / gp) if gp else 0.0,
                "avg_pa": fmt_score(total_pa[t] / gp) if gp else 0.0,
                "champion": "Yes" if t == champion else "No",
            }
        )

    # Sort standings by regular season performance (wins desc, then total_pf desc)
    standings_data.sort(key=lambda x: (-x["wins"], -x["total_pf"]))

    # ── PLAYOFF_BRACKET data ──────────────────────────────────────────────────
    def bracket_match(
        match_id: int,
        round_num: int,
        team_a: str,
        team_b: str,
        winner: str,
        loser: str,
        from_a: str | None,
        from_b: str | None,
        position: int | None,
    ) -> dict:
        oa, ob = owner_by_id[team_a], owner_by_id[team_b]
        return {
            "match_id": match_id,
            "round": round_num,
            "team_1_id": team_a,
            "team_1_display_name": oa["username"],
            "team_1_team_name": oa["team_name"],
            "team_1_team_logo": None,
            "team_2_id": team_b,
            "team_2_display_name": ob["username"],
            "team_2_team_name": ob["team_name"],
            "team_2_team_logo": None,
            "winner": winner,
            "loser": loser,
            "position": position,
            "team_1_from": from_a,
            "team_2_from": from_b,
        }

    bracket_data = [
        bracket_match(1, 1, s1, s4, m1["winner"], m1["loser"], None, None, None),
        bracket_match(2, 1, s2, s3, m2["winner"], m2["loser"], None, None, None),
        bracket_match(
            3,
            2,
            sf1_winner,
            sf2_winner,
            m3["winner"],
            m3["loser"],
            '{"w": 1}',
            '{"w": 2}',
            1,
        ),
    ]

    return {
        "reg_matchups": reg_matchups,  # list of N_REG_WEEKS lists of matchup dicts
        "week16_matchups": week16_matchups,
        "week17_matchups": week17_matchups,
        "standings_data": standings_data,
        "weekly_snapshots": weekly_snapshots,
        "bracket_data": bracket_data,
        "final_rank": final_rank,
        "wins": wins,
        "total_pf": total_pf,
    }


# ── DynamoDB item builders ────────────────────────────────────────────────────


def build_season_items(
    season: str,
    owners: list[dict],
    draft_picks: list[dict],
    rosters: dict[str, list[tuple[str, dict]]],
    all_scores: dict[str, dict[int, dict[int, float]]],
    sim: dict,
) -> list[dict]:
    """Build all DynamoDB items for one season."""
    pk = f"LEAGUE#{DEMO_CANONICAL_ID}"
    items: list[dict] = []

    # ── TEAMS ─────────────────────────────────────────────────────────────────
    teams_data = [
        sanitize_value(
            {
                "display_name": o["username"],
                "team_id": o["id"],
                "team_name": o["team_name"],
                "team_logo": None,
                "season": season,
                "primary_owner_id": o["owner_id"],
                "secondary_owner_id": None,
                "final_rank": sim["final_rank"][o["id"]],
            }
        )
        for o in owners
    ]
    items.append({"PK": pk, "SK": f"TEAMS#{season}", "data": teams_data})

    # ── MATCHUPS ──────────────────────────────────────────────────────────────
    def stamp(matchups: list[dict]) -> list[dict]:
        out = []
        for m in matchups:
            mc = dict(m)
            mc["season"] = season
            out.append(sanitize_value(mc))
        return out

    for week_idx, week_matchups in enumerate(sim["reg_matchups"]):
        week = week_idx + 1
        items.append(
            {
                "PK": pk,
                "SK": f"MATCHUPS#{season}#WEEK#{week:02d}",
                "data": stamp(week_matchups),
            }
        )

    for week, week_matchups in [
        (16, sim["week16_matchups"]),
        (17, sim["week17_matchups"]),
    ]:
        items.append(
            {
                "PK": pk,
                "SK": f"MATCHUPS#{season}#WEEK#{week:02d}",
                "data": stamp(week_matchups),
            }
        )

    # ── STANDINGS ─────────────────────────────────────────────────────────────
    standings_stamped = [
        sanitize_value(dict(row, season=season)) for row in sim["standings_data"]
    ]
    items.append({"PK": pk, "SK": f"STANDINGS#{season}", "data": standings_stamped})

    # ── WEEKLY_STANDINGS ──────────────────────────────────────────────────────
    ws_stamped = [
        sanitize_value(dict(row, season=season)) for row in sim["weekly_snapshots"]
    ]
    items.append({"PK": pk, "SK": f"WEEKLY_STANDINGS#{season}", "data": ws_stamped})

    # ── PLAYOFF_BRACKET ───────────────────────────────────────────────────────
    bracket_stamped = [
        sanitize_value(dict(row, season=season)) for row in sim["bracket_data"]
    ]
    items.append({"PK": pk, "SK": f"PLAYOFF_BRACKET#{season}", "data": bracket_stamped})

    # ── LEAGUE_SETTINGS ───────────────────────────────────────────────────────
    # Per-season playoff configuration backing the playoff-race predictor's cutoff
    # line and its last-3-weeks replay in demo mode.
    items.append(
        {
            "PK": pk,
            "SK": f"LEAGUE_SETTINGS#{season}",
            "data": [
                sanitize_value(
                    {
                        "season": season,
                        "num_playoff_teams": N_PLAYOFF_TEAMS,
                        "num_playoff_teams_assumed": False,
                        "playoff_week_start": N_REG_WEEKS + 1,
                        "regular_season_weeks": N_REG_WEEKS,
                    }
                )
            ],
        }
    )

    # ── DRAFT ─────────────────────────────────────────────────────────────────
    # Compute total_points per player (sum of regular-season weekly scores)
    # For non-rostered weeks or bye weeks: use generated score regardless
    player_totals: dict[str, dict[int, float]] = {}  # team_id → player_id → total
    for team_id, roster in rosters.items():
        player_totals[team_id] = {}
        for _, player in roster:
            pid = player["player_id"]
            total = sum(
                all_scores[team_id][w][pid]
                for w in range(1, N_REG_WEEKS + 1)  # regular season only
            )
            player_totals[team_id][pid] = fmt_score(total)

    # Actual position ranks (by total_points among all drafted players at that position)
    pos_totals: dict[str, list[tuple[int, float]]] = {}  # pos → [(pid, total)]
    for team_id, roster in rosters.items():
        for pos, player in roster:
            pid = player["player_id"]
            pos_totals.setdefault(pos, []).append((pid, player_totals[team_id][pid]))

    actual_rank: dict[str, dict[int, int]] = {}  # pos → pid → rank
    for pos, entries in pos_totals.items():
        entries.sort(key=lambda x: -x[1])
        actual_rank[pos] = {pid: i + 1 for i, (pid, _) in enumerate(entries)}

    # Replacement level
    repl_rank = {"QB": 11, "RB": 13, "WR": 13, "TE": 11, "K": 11, "D/ST": 11}
    replacement_level: dict[str, float] = {}
    for pos, entries in pos_totals.items():
        entries.sort(key=lambda x: -x[1])
        idx = min(repl_rank.get(pos, 11), len(entries)) - 1
        replacement_level[pos] = entries[idx][1] if entries else 0.0

    # Drafted position ranks: rank by draft position within position
    drafted_rank: dict[str, dict[int, int]] = {}
    pos_pick_order: dict[str, list[int]] = {}
    for pick in draft_picks:
        pos = pick["position"]
        pos_pick_order.setdefault(pos, []).append(pick["player_id"])
    for pos, pids in pos_pick_order.items():
        drafted_rank[pos] = {pid: i + 1 for i, pid in enumerate(pids)}

    draft_data = []
    for pick in draft_picks:
        pos = pick["position"]
        pid = pick["player_id"]
        team_id = pick["team_id"]
        total = player_totals[team_id][pid]
        ar = actual_rank.get(pos, {}).get(pid, 0)
        dr = drafted_rank.get(pos, {}).get(pid, 0)
        repl = replacement_level.get(pos, 0.0)
        vorp = fmt_score(total - repl) if repl else None
        draft_data.append(
            sanitize_value(
                {
                    "team_id": team_id,
                    "owner_id": pick["owner_id"],
                    "owner_username": pick["owner_username"],
                    "team_name": pick["team_name"],
                    "team_logo": None,
                    "pick_id": pick["overall_pick_number"],
                    "round": pick["round"],
                    "round_pick_number": pick["round_pick_number"],
                    "overall_pick_number": pick["overall_pick_number"],
                    "player_id": str(pid),
                    "player_name": pick["player_name"],
                    "position": pos,
                    "total_points": total,
                    "keeper": False,
                    "reserved_for_keeper": False,
                    "auto_draft_type_id": 0,
                    "bid_amount": 0,
                    "is_auction": False,
                    "lineup_slot_id": 0,
                    "member_id": pick["owner_id"],
                    "nominating_team_id": 0,
                    "trade_locked": False,
                    "season": season,
                    "drafted_position_rank": dr,
                    "actual_position_rank": ar,
                    "draft_rank_delta": dr - ar,
                    "vorp": vorp,
                }
            )
        )

    items.append({"PK": pk, "SK": f"DRAFT#{season}", "data": draft_data})

    # Separate auction-format draft dataset (DRAFT_AUCTION#<season>), demo only.
    # Seeded per season so the bids are deterministic across runs.
    auction_rng = random.Random(SEED + int(season))  # noqa: S311 — demo data, not crypto
    auction_data = build_auction_draft_rows(draft_data, auction_rng)
    items.append({"PK": pk, "SK": f"DRAFT_AUCTION#{season}", "data": auction_data})

    return items


# ── Transactions (Sleeper only) ───────────────────────────────────────────────


def _txn_created_ms(season: str, week: int, rng: random.Random) -> int:
    """Unix epoch milliseconds for a transaction in a given season/week.

    Anchored to early September of the season, advancing one week per game week
    with a little intra-week jitter so cards sort believably newest-first.
    """
    base = datetime.datetime(int(season), 9, 4, tzinfo=datetime.timezone.utc)
    dt = base + datetime.timedelta(days=(week - 1) * 7, hours=rng.uniform(0, 72))
    return int(dt.timestamp() * 1000)


def _txn_player(player: dict, pos: str, roster_id: str) -> dict:
    """A TransactionPlayer row (player_id is a string on the wire, per frontend/transactions)."""
    return {
        "player_id": str(player["player_id"]),
        "player_name": player["full_name"],
        "position": pos,
        "roster_id": roster_id,
    }


def build_transactions(
    season: str,
    owners: list[dict],
    rosters: dict[str, list[tuple[str, dict]]],
    draft_picks: list[dict],
    rng: random.Random,
) -> list[dict]:
    """Synthesize a Sleeper season's transactions (backend/sleeper-transactions / frontend/transactions).

    For each game week, generates a handful of waiver/free-agent adds (each
    dropping a player already on the roster and adding an undrafted free agent)
    plus the occasional trade — sometimes including a future-season draft pick.
    Roster movements stay coherent (a dropped player rejoins the free-agent pool,
    a traded player swaps rosters), and roster_id == team_id, matching the
    Sleeper standings/teams so the page's avatars line up.
    """
    team_ids = [o["id"] for o in owners]
    teams_meta_by_id = {
        o["id"]: {
            "roster_id": o["id"],
            "team_name": o["team_name"],
            "display_name": o["username"],
        }
        for o in owners
    }

    drafted_ids = {int(p["player_id"]) for p in draft_picks}
    free_agents: list[tuple[str, dict]] = [
        (pos, player)
        for pos, players in PLAYER_POOL.items()
        for player in players
        if player["player_id"] not in drafted_ids
    ]
    rng.shuffle(free_agents)
    fa_idx = 0

    def next_free_agent() -> tuple[str, dict]:
        nonlocal fa_idx
        if fa_idx >= len(free_agents):
            rng.shuffle(free_agents)
            fa_idx = 0
        entry = free_agents[fa_idx]
        fa_idx += 1
        return entry

    roster_players = {tid: list(roster) for tid, roster in rosters.items()}

    transactions: list[dict] = []
    counter = 0

    def make_id() -> str:
        nonlocal counter
        counter += 1
        return f"demo-txn-{season}-{counter:03d}"

    for week in range(1, N_REG_WEEKS + 1):
        # Waiver / free-agent adds for the week.
        for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
            tid = rng.choice(team_ids)
            roster = roster_players[tid]
            if not roster:
                continue
            drop_pos, drop_player = roster.pop(rng.randrange(len(roster)))
            add_pos, add_player = next_free_agent()
            roster.append((add_pos, add_player))
            free_agents.append((drop_pos, drop_player))  # dropped → back to pool
            is_waiver = rng.random() < 0.5
            transactions.append(
                {
                    "season": season,
                    "transaction_id": make_id(),
                    "type": "waiver" if is_waiver else "free_agent",
                    "week": week,
                    "created": _txn_created_ms(season, week, rng),
                    "roster_ids": [tid],
                    "teams": [teams_meta_by_id[tid]],
                    "adds": [_txn_player(add_player, add_pos, tid)],
                    "drops": [_txn_player(drop_player, drop_pos, tid)],
                    "draft_picks": [],
                    "waiver_bid": rng.choice([3, 5, 8, 12, 17, 23])
                    if is_waiver
                    else None,
                }
            )

        # Occasional trade between two rosters.
        if rng.random() < 0.25:
            a, b = rng.sample(team_ids, 2)
            ra, rb = roster_players[a], roster_players[b]
            if ra and rb:
                pa_pos, pa = ra.pop(rng.randrange(len(ra)))
                pb_pos, pb = rb.pop(rng.randrange(len(rb)))
                ra.append((pb_pos, pb))
                rb.append((pa_pos, pa))
                draft_picks_traded: list[dict] = []
                if rng.random() < 0.3:
                    draft_picks_traded.append(
                        {
                            "round": rng.randint(1, 5),
                            "season": str(int(season) + 1),
                            "from_roster_id": b,
                            "to_roster_id": a,
                        }
                    )
                transactions.append(
                    {
                        "season": season,
                        "transaction_id": make_id(),
                        "type": "trade",
                        "week": week,
                        "created": _txn_created_ms(season, week, rng),
                        "roster_ids": [a, b],
                        "teams": [teams_meta_by_id[a], teams_meta_by_id[b]],
                        # Each team receives the other's player; drops are the
                        # players each side sends away.
                        "adds": [
                            _txn_player(pb, pb_pos, a),
                            _txn_player(pa, pa_pos, b),
                        ],
                        "drops": [
                            _txn_player(pa, pa_pos, a),
                            _txn_player(pb, pb_pos, b),
                        ],
                        "draft_picks": draft_picks_traded,
                        "waiver_bid": None,
                    }
                )

    transactions.sort(
        key=lambda t: -t["created"]
    )  # newest-first, per backend/sleeper-transactions
    return [sanitize_value(t) for t in transactions]


# ── Main seeding logic ────────────────────────────────────────────────────────


def build_all_items() -> list[dict]:
    items: list[dict] = []

    # ESPN LEAGUE_LOOKUP (2022–2024)
    items.append(
        {
            "PK": f"LEAGUE#{DEMO_LEAGUE_ID}#PLATFORM#{PLATFORM}",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": DEMO_CANONICAL_ID,
            "seasons": set(SEASONS),
        }
    )

    # Sleeper LEAGUE_LOOKUP (2025)
    items.append(
        {
            "PK": f"LEAGUE#{DEMO_SLEEPER_LEAGUE_ID}#PLATFORM#{SLEEPER_PLATFORM}",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": DEMO_CANONICAL_ID,
            "seasons": set(SLEEPER_SEASONS),
        }
    )

    # METADATA — updated post-migration fields
    items.append(
        {
            "PK": f"LEAGUE#{DEMO_CANONICAL_ID}",
            "SK": "METADATA",
            "platform": SLEEPER_PLATFORM,
            "active_platform": SLEEPER_PLATFORM,
            "migrated_from": PLATFORM,
            "migrated_at": MIGRATED_AT,
            "league_name": DEMO_LEAGUE_NAME,
            "onboarded_at": ONBOARDED_AT,
        }
    )

    # PLATFORM_MIGRATION item — ESPN owner_id → Sleeper owner_id mapping
    items.append(
        {
            "PK": f"LEAGUE#{DEMO_CANONICAL_ID}",
            "SK": f"PLATFORM_MIGRATION#{PLATFORM}#{SLEEPER_PLATFORM}",
            "data": get_migration_mapping(),
        }
    )

    prev_standings: list[dict] | None = None

    # ESPN seasons 2022–2024
    for season_idx, season in enumerate(SEASONS):
        rng = random.Random(SEED + season_idx)  # noqa: S311 — demo data, not crypto
        owners = get_owners(season)
        logger.info("Season %s: drafting and simulating...", season)

        draft_picks, rosters = build_draft(owners, rng, prev_standings)

        # Generate scores for all 17 weeks
        all_scores = gen_weekly_scores(rosters, N_REG_WEEKS + 2, rng)

        sim = simulate_season(owners, rosters, all_scores, rng)

        season_items = build_season_items(
            season, owners, draft_picks, rosters, all_scores, sim
        )
        items.extend(season_items)

        prev_standings = sim["standings_data"]

    # Sleeper season 2025
    sleeper_owners = get_sleeper_owners()
    rng_2025 = random.Random(SEED + len(SEASONS))  # noqa: S311 — demo data, not crypto
    logger.info("Season 2025 (Sleeper): drafting and simulating...")
    draft_picks_2025, rosters_2025 = build_draft(
        sleeper_owners, rng_2025, prev_standings
    )
    all_scores_2025 = gen_weekly_scores(rosters_2025, N_REG_WEEKS + 2, rng_2025)
    sim_2025 = simulate_season(sleeper_owners, rosters_2025, all_scores_2025, rng_2025)
    season_items_2025 = build_season_items(
        "2025",
        sleeper_owners,
        draft_picks_2025,
        rosters_2025,
        all_scores_2025,
        sim_2025,
    )
    items.extend(season_items_2025)

    # Transactions are Sleeper-only (ESPN exposes none), so they exist only for
    # the 2025 Sleeper season. Seeded separately so bids/timestamps are stable.
    txn_rng = random.Random(SEED + 100)  # noqa: S311 — demo data, not crypto
    txn_data = build_transactions(
        "2025", sleeper_owners, rosters_2025, draft_picks_2025, txn_rng
    )
    items.append(
        {
            "PK": f"LEAGUE#{DEMO_CANONICAL_ID}",
            "SK": "TRANSACTIONS#2025",
            "data": txn_data,
        }
    )

    return items


class _JsonEncoder(json.JSONEncoder):
    """Converts Decimal → float and set → sorted list for JSON serialisation."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, set):
            return sorted(obj)
        return super().default(obj)


def build_demo_json() -> dict:
    """Return the full demo dataset as a JSON-serialisable dict."""
    items = build_all_items()
    by_sk = {
        item["SK"]: json.loads(json.dumps(item.get("data", []), cls=_JsonEncoder))
        for item in items
        if item.get("data")
    }
    return {"league_name": DEMO_LEAGUE_NAME, "data": by_sk}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate frontend/src/lib/demo-data.json from the demo seed data."
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help=f"Output path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a summary without writing the file.",
    )
    args = parser.parse_args()

    payload = build_demo_json()
    total_rows = sum(len(v) for v in payload["data"].values())
    logger.info(
        "Generated %d SK buckets, %d total rows.", len(payload["data"]), total_rows
    )

    if args.dry_run:
        for sk, rows in sorted(payload["data"].items()):
            logger.info("  %-45s  %d rows", sk, len(rows))
        logger.info("DRY RUN — file not written.")
        return

    out: pathlib.Path = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    logger.info("Written to %s (%d bytes).", out, out.stat().st_size)


if __name__ == "__main__":
    main()
