"""
seed_demo_data.py

Populate DynamoDB with 3 seasons of demo ESPN fantasy football data
for the LeagueQL app.

Usage:
    pipenv run python deployment_scripts/seed_demo_data.py --env dev --dry-run
    pipenv run python deployment_scripts/seed_demo_data.py --env prod
    pipenv run python deployment_scripts/seed_demo_data.py --env dev --delete
"""

import argparse
import logging
import random
from decimal import Decimal
from typing import Any

import boto3

# ── Constants ─────────────────────────────────────────────────────────────────

SEED = 42
DEMO_LEAGUE_ID = "999999999"
DEMO_CANONICAL_ID = "demo-league-canonical"
DEMO_LEAGUE_NAME = "Demo Fantasy League"
PLATFORM = "ESPN"
SEASONS = ["2022", "2023", "2024"]
ONBOARDED_AT = "2024-09-01T00:00:00"
N_REG_WEEKS = 14
N_TEAMS = 10
N_PLAYOFF_TEAMS = 6
N_BYE_TEAMS = 2
DRAFT_ROUNDS = 14

TABLE_NAMES = {
    "dev": "fantasy-football-recap-table-dev",
    "prod": "fantasy-football-recap-table-prod",
}

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

    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: -x[2])

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
    Run regular season (weeks 1-14), determine playoff seeds, run playoffs.
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

    # Determine playoff seeds (top 6 by wins, tiebreak: total PF)
    sorted_teams = sorted(team_ids, key=lambda t: (-wins[t], -total_pf[t]))
    playoff_seeds = sorted_teams[:N_PLAYOFF_TEAMS]  # [seed1, seed2, ...]
    consolation_teams = sorted_teams[N_PLAYOFF_TEAMS:]

    # ── Playoffs ──────────────────────────────────────────────────────────────
    # Seeds 1 and 2 have byes in week 15 (Quarterfinals)
    s1, s2 = playoff_seeds[0], playoff_seeds[1]
    s3, s4, s5, s6 = (
        playoff_seeds[2],
        playoff_seeds[3],
        playoff_seeds[4],
        playoff_seeds[5],
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

    # Week 15 — Quarterfinals (seeds 3-6) + consolation (seeds 7-10)
    m1 = playoff_matchup(s3, s6, 15, "WINNERS_BRACKET", "Quarterfinals")
    m2 = playoff_matchup(s4, s5, 15, "WINNERS_BRACKET", "Quarterfinals")
    c1, c2, c3, c4 = consolation_teams  # seeds 7-10
    mc1 = playoff_matchup(c1, c2, 15, "WINNERS_CONSOLATION_LADDER", None)
    mc2 = playoff_matchup(c3, c4, 15, "WINNERS_CONSOLATION_LADDER", None)
    week15_matchups = [m1, m2, mc1, mc2]

    # Week 16 — Semifinals + 5th-place game + consolation round 2
    qf1_winner, qf1_loser = m1["winner"], m1["loser"]
    qf2_winner, qf2_loser = m2["winner"], m2["loser"]
    m3 = playoff_matchup(s1, qf2_winner, 16, "WINNERS_BRACKET", "Semifinals")
    m4 = playoff_matchup(s2, qf1_winner, 16, "WINNERS_BRACKET", "Semifinals")
    m5 = playoff_matchup(qf1_loser, qf2_loser, 16, "WINNERS_CONSOLATION_LADDER", None)
    mc3 = playoff_matchup(
        mc1["winner"], mc2["winner"], 16, "WINNERS_CONSOLATION_LADDER", None
    )
    mc4 = playoff_matchup(
        mc1["loser"], mc2["loser"], 16, "WINNERS_CONSOLATION_LADDER", None
    )
    week16_matchups = [m3, m4, m5, mc3, mc4]

    # Week 17 — Championship + 3rd place + consolation finals
    sf1_winner, sf1_loser = m3["winner"], m3["loser"]
    sf2_winner, sf2_loser = m4["winner"], m4["loser"]
    m6 = playoff_matchup(sf1_winner, sf2_winner, 17, "WINNERS_BRACKET", "Finals")
    m7 = playoff_matchup(sf1_loser, sf2_loser, 17, "WINNERS_BRACKET", None)
    mc5 = playoff_matchup(
        mc3["winner"], m5["winner"], 17, "WINNERS_CONSOLATION_LADDER", None
    )
    mc6 = playoff_matchup(
        mc3["loser"], m5["loser"], 17, "WINNERS_CONSOLATION_LADDER", None
    )
    mc7 = playoff_matchup(
        mc4["winner"], mc4["loser"], 17, "WINNERS_CONSOLATION_LADDER", None
    )
    week17_matchups = [m6, m7, mc5, mc6, mc7]

    champion = m6["winner"]

    # ── Final rankings ────────────────────────────────────────────────────────
    qf_losers_by_seed = [
        t for t in [qf1_loser, qf2_loser] if t in [qf1_loser, qf2_loser]
    ]
    # sort QF losers by regular season record
    qf_losers_by_seed.sort(key=lambda t: (-wins[t], -total_pf[t]))

    final_rank: dict[str, int] = {}
    final_rank[m6["winner"]] = 1
    final_rank[m6["loser"]] = 2
    final_rank[m7["winner"]] = 3
    final_rank[m7["loser"]] = 4
    for i, t in enumerate(qf_losers_by_seed):
        final_rank[t] = 5 + i
    for i, t in enumerate(consolation_teams):
        final_rank[t] = 7 + i

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
        bracket_match(1, 1, s3, s6, m1["winner"], m1["loser"], None, None, None),
        bracket_match(2, 1, s4, s5, m2["winner"], m2["loser"], None, None, None),
        bracket_match(
            3, 2, s1, qf2_winner, m3["winner"], m3["loser"], None, '{"w": 1}', None
        ),
        bracket_match(
            4, 2, s2, qf1_winner, m4["winner"], m4["loser"], None, '{"w": 2}', None
        ),
        bracket_match(
            5,
            2,
            qf1_loser,
            qf2_loser,
            m5["winner"],
            m5["loser"],
            '{"l": 1}',
            '{"l": 2}',
            5,
        ),
        bracket_match(
            6,
            3,
            sf1_winner,
            sf2_winner,
            m6["winner"],
            m6["loser"],
            '{"w": 3}',
            '{"w": 4}',
            1,
        ),
        bracket_match(
            7,
            3,
            sf1_loser,
            sf2_loser,
            m7["winner"],
            m7["loser"],
            '{"l": 3}',
            '{"l": 4}',
            3,
        ),
    ]

    return {
        "reg_matchups": reg_matchups,  # list of 14 lists of matchup dicts
        "week15_matchups": week15_matchups,
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
        (15, sim["week15_matchups"]),
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

    # ── DRAFT ─────────────────────────────────────────────────────────────────
    # Compute total_points per player (sum of all weekly scores, weeks 1-17)
    # For non-rostered weeks or bye weeks: use generated score regardless
    player_totals: dict[str, dict[int, float]] = {}  # team_id → player_id → total
    for team_id, roster in rosters.items():
        player_totals[team_id] = {}
        for _, player in roster:
            pid = player["player_id"]
            total = sum(
                all_scores[team_id][w][pid]
                for w in range(1, 15)  # regular season only for total_points
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

    return items


# ── Main seeding logic ────────────────────────────────────────────────────────


def build_all_items() -> list[dict]:
    items: list[dict] = []

    # LEAGUE_LOOKUP
    items.append(
        {
            "PK": f"LEAGUE#{DEMO_LEAGUE_ID}#PLATFORM#{PLATFORM}",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": DEMO_CANONICAL_ID,
            "seasons": set(SEASONS),
        }
    )

    # METADATA
    items.append(
        {
            "PK": f"LEAGUE#{DEMO_CANONICAL_ID}",
            "SK": "METADATA",
            "platform": PLATFORM,
            "league_name": DEMO_LEAGUE_NAME,
            "onboarding_status": "COMPLETED",
            "onboarded_at": ONBOARDED_AT,
        }
    )

    prev_standings: list[dict] | None = None

    for season_idx, season in enumerate(SEASONS):
        rng = random.Random(SEED + season_idx)
        owners = get_owners(season)
        logger.info("Season %s: drafting and simulating...", season)

        draft_picks, rosters = build_draft(owners, rng, prev_standings)

        # Generate scores for all 17 weeks
        all_scores = gen_weekly_scores(rosters, N_REG_WEEKS + 3, rng)

        sim = simulate_season(owners, rosters, all_scores, rng)

        season_items = build_season_items(
            season, owners, draft_picks, rosters, all_scores, sim
        )
        items.extend(season_items)

        prev_standings = sim["standings_data"]

    return items


def write_items(table: Any, items: list[dict], dry_run: bool) -> None:
    if dry_run:
        logger.info("DRY RUN — %d items would be written:", len(items))
        for item in items:
            sk = item.get("SK", "?")
            data_len = len(item.get("data", []))
            if data_len:
                logger.info("  %s  (data rows: %d)", sk, data_len)
            else:
                logger.info("  %s", sk)
        return

    logger.info("Writing %d items to DynamoDB...", len(items))
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    logger.info("Done.")


def delete_demo_data(table: Any, dry_run: bool) -> None:
    """Delete all demo data from DynamoDB."""
    pk = f"LEAGUE#{DEMO_CANONICAL_ID}"
    lookup_pk = f"LEAGUE#{DEMO_LEAGUE_ID}#PLATFORM#{PLATFORM}"

    if dry_run:
        logger.info("DRY RUN — Would delete all items with PK: %s", pk)
        logger.info("DRY RUN — Would delete LEAGUE_LOOKUP item with PK: %s", lookup_pk)
        return

    logger.info("Deleting demo data with PK: %s", pk)

    # Query all items with the demo league PK
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("PK").eq(pk)
    )
    items = response.get("Items", [])

    # Handle pagination if there are more items
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("PK").eq(pk),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    logger.info("Found %d items to delete", len(items))

    # Delete all items with batch writer
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    # Delete the LEAGUE_LOOKUP item
    logger.info("Deleting LEAGUE_LOOKUP item...")
    table.delete_item(Key={"PK": lookup_pk, "SK": "LEAGUE_LOOKUP"})

    logger.info("Deleted %d demo data items.", len(items))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed or delete LeagueQL demo data in DynamoDB."
    )
    parser.add_argument(
        "--env", choices=["dev", "prod"], required=True, help="Target environment"
    )
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print items without writing to DynamoDB"
    )
    parser.add_argument(
        "--delete", action="store_true", help="Delete demo data instead of seeding"
    )
    args = parser.parse_args()

    table_name = TABLE_NAMES[args.env]
    logger.info("Target table: %s", table_name)

    if args.delete:
        dynamodb = boto3.resource("dynamodb", region_name=args.region)
        table = dynamodb.Table(table_name)
        delete_demo_data(table, dry_run=args.dry_run)
        return

    items = build_all_items()
    logger.info("Generated %d total DynamoDB items.", len(items))

    if args.dry_run:
        write_items(None, items, dry_run=True)
        return

    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    table = dynamodb.Table(table_name)
    write_items(table, items, dry_run=False)


if __name__ == "__main__":
    main()
