import asyncio
import random
from collections import defaultdict
from datetime import datetime

from anthropic import AsyncAnthropic, RateLimitError
from anthropic.types import TextBlock

from logging_utils import logger


def build_season_recap_prompt(
    season: str,
    standings_rows: list[dict],
    matchup_rows: list[dict],
) -> str:
    """
    Build a prompt for Claude to generate a fantasy football season recap.

    Args:
        season: The season year (e.g., "2024").
        standings_rows: List of row dicts from the STANDINGS DuckDB output.
        matchup_rows: List of row dicts from the MATCHUPS DuckDB output.

    Returns:
        A prompt string for Claude.
    """
    standings_sorted = sorted(
        standings_rows,
        key=lambda r: (-r.get("wins", 0), -float(r.get("total_pf", 0))),
    )

    champion_row = next((r for r in standings_rows if r.get("champion") == "Yes"), None)
    season_complete = champion_row is not None

    header = "Rank | Owner | Team | Record | Avg PF | Avg PA | Win% | Win% vs League | Champion"
    divider = "-" * 90
    standings_lines = [header, divider]
    for rank, row in enumerate(standings_sorted, 1):
        champion_marker = " *** CHAMPION ***" if row.get("champion") == "Yes" else ""
        standings_lines.append(
            f"{rank} | {row['owner_username']} | {row['team_name']} | "
            f"{row['record']} | {float(row['avg_pf']):.2f} | {float(row['avg_pa']):.2f} | "
            f"{float(row['win_pct']):.3f} | {float(row['win_pct_vs_league']):.3f}"
            f"{champion_marker}"
        )

    team_label: dict[str, str] = {
        row["team_id"]: f"{row['owner_username']} ({row['team_name']})"
        for row in standings_rows
    }

    by_week: dict[str, list[dict]] = defaultdict(list)
    for m in matchup_rows:
        by_week[str(m["week"])].append(m)

    matchup_lines: list[str] = []
    for week in sorted(by_week.keys(), key=lambda w: int(w) if w.isdigit() else 0):
        matchup_lines.append(f"Week {week}:")
        for m in by_week[week]:
            a_label = team_label.get(str(m["team_a_id"]), str(m["team_a_id"]))
            b_label = team_label.get(str(m["team_b_id"]), str(m["team_b_id"]))
            a_score = float(m["team_a_score"])
            b_score = float(m["team_b_score"])
            winner_id = str(m["winner"])
            if winner_id == str(m["team_a_id"]):
                result_text = f"{a_label} wins"
            elif winner_id == str(m["team_b_id"]):
                result_text = f"{b_label} wins"
            else:
                result_text = "TIE"
            matchup_lines.append(
                f"  {a_label} ({a_score:.2f}) vs {b_label} ({b_score:.2f}) — {result_text}"
            )

    playoff_start_week = 15 if int(season) >= 2021 else 14

    if season_complete:
        champion_name = (
            f"{champion_row['owner_username']} ({champion_row['team_name']})"
        )
        task_description = (
            f"Write exactly 3 paragraphs recapping the {season} fantasy football season. "
            f"Note: the playoffs began in week {playoff_start_week}.\n\n"
            f"Paragraph 1 — The Champion: Focus on {champion_name}, who won the title. "
            f"Celebrate and lightly roast their path to glory — were they dominant or lucky?\n\n"
            f"Paragraph 2 — The Playoffs: Recap how the playoff bracket played out. "
            f"Who had a memorable run? Who choked? Any shocking upsets?\n\n"
            f"Paragraph 3 — Season Highlights & Lowlights: Cover the most notable moments "
            f"from the regular season — big scoring weeks, embarrassing losses, bad beats, "
            f"and anything else worth remembering (or forgetting)."
        )
    else:
        task_description = (
            f"Write exactly 3 paragraphs as a mid-season report for the {season} fantasy football season, "
            f"which is still in progress. Note: the playoffs begin in week {playoff_start_week}.\n\n"
            f"Paragraph 1 — Playoff Picture: Who is locked in, who is on the bubble, "
            f"and who is already cooked?\n\n"
            f"Paragraph 2 — Best Teams So Far: Who has been genuinely good vs. just lucky? "
            f"Break down the contenders.\n\n"
            f"Paragraph 3 — Highlights & Lowlights: The most notable moments so far — "
            f"big scores, brutal losses, bad beats, and anything else worth remembering."
        )

    prompt = (
        f"You are a fantasy football analyst with the wit of a late-night comedian and the "
        f"insight of a seasoned sports writer. Be funny and roast-y — ground every joke in "
        f"the actual data. Do not use headers, titles, or bullet points. Do not begin with a "
        f"title or heading of any kind. Write in flowing prose only, with a blank line between "
        f"each paragraph.\n\n"
        f"{task_description}\n\n"
        f"Season Standings:\n{chr(10).join(standings_lines)}\n\n"
        f"Weekly Matchups:\n{chr(10).join(matchup_lines)}\n\n"
        "Write the recap now:"
    )
    return prompt


_MAX_RETRIES = 4
_BASE_DELAY = 2.0
_MAX_DELAY = 60.0


async def generate_single_recap(
    client: AsyncAnthropic,
    season: str,
    prompt: str,
) -> dict:
    """
    Call Claude to generate a recap for a single season, with exponential
    backoff retries on rate limit errors (HTTP 429).

    Args:
        client: An AsyncAnthropic client instance.
        season: The season year.
        prompt: The prompt to send to Claude.

    Returns:
        A dict with recap_text, generated_at, and season.
    """
    delay = _BASE_DELAY
    for attempt in range(_MAX_RETRIES + 1):
        try:
            message = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            content_block = message.content[0]
            if not isinstance(content_block, TextBlock):
                raise ValueError(
                    f"Unexpected content block type: {type(content_block)}"
                )
            return {
                "season": season,
                "recap_text": content_block.text,
                "generated_at": datetime.now().isoformat() + "Z",
            }
        except RateLimitError:
            if attempt == _MAX_RETRIES:
                raise
            jitter = random.uniform(0, delay * 0.1)
            wait = delay + jitter
            logger.warning(
                "Rate limited generating recap for season %s, retrying in %.1fs "
                "(attempt %d/%d)",
                season,
                wait,
                attempt + 1,
                _MAX_RETRIES,
            )
            await asyncio.sleep(wait)
            delay = min(delay * 2, _MAX_DELAY)
    raise RuntimeError("generate_single_recap exited retry loop without returning")


async def generate_recaps_for_all_seasons(
    table,
    api_key: str,
    pk: str,
    seasons: list[str],
    standings_by_season: dict[str, list[dict]],
    matchups_by_season: dict[str, list[dict]],
) -> None:
    """
    Generate and store AI recaps for the given seasons.

    Always overwrites existing recap items. Seasons with no standings data are
    skipped. Failures for individual seasons are logged without raising.

    Args:
        table: A boto3 DynamoDB Table resource.
        api_key: The Anthropic API key.
        pk: The DynamoDB partition key (e.g., "LEAGUE#abc123").
        seasons: List of seasons to generate recaps for.
        standings_by_season: Dict mapping season -> list of standings row dicts.
        matchups_by_season: Dict mapping season -> list of matchup row dicts.
    """
    client = AsyncAnthropic(api_key=api_key)

    prompts: dict[str, str] = {}
    for season in seasons:
        s_rows = standings_by_season.get(season, [])
        m_rows = matchups_by_season.get(season, [])
        if not s_rows:
            logger.warning("No standings data for season %s, skipping recap", season)
            continue
        prompts[season] = build_season_recap_prompt(
            season=season,
            standings_rows=s_rows,
            matchup_rows=m_rows,
        )

    seasons_with_prompts = list(prompts.keys())
    if not seasons_with_prompts:
        return

    logger.info("Generating AI recaps for seasons: %s", seasons_with_prompts)
    results = await asyncio.gather(
        *[
            generate_single_recap(client, season, prompts[season])
            for season in seasons_with_prompts
        ],
        return_exceptions=True,
    )

    for season, result in zip(seasons_with_prompts, results):
        if isinstance(result, Exception):
            logger.error("Failed to generate recap for season %s: %s", season, result)
            continue
        table.put_item(
            Item={
                "PK": pk,
                "SK": f"AI_RECAP#{season}",
                "data": [result],
            }
        )
        logger.info("Stored AI recap for season %s", season)


def build_manager_recap_prompt(
    owner_id: str,
    owner_username: str,
    owner_standings: list[dict],
    owner_matchups: list[dict],
    all_owner_usernames: dict[str, str],
) -> str:
    """
    Build a prompt for Claude to generate a fantasy football manager career retrospective.

    Args:
        owner_id: Platform user ID of the manager.
        owner_username: Display name of the manager.
        owner_standings: All seasons' standings rows for this owner.
        owner_matchups: All matchups involving this owner as team_a or team_b.
        all_owner_usernames: Mapping of owner_id -> username for all league members.

    Returns:
        A prompt string for Claude.
    """
    total_wins = sum(int(r["wins"]) for r in owner_standings)
    total_losses = sum(int(r["losses"]) for r in owner_standings)
    total_games = sum(int(r["games_played"]) for r in owner_standings)
    total_pf = sum(float(r["total_pf"]) for r in owner_standings)
    championships = sum(1 for r in owner_standings if r.get("champion") == "Yes")
    avg_pf = total_pf / total_games if total_games > 0 else 0.0
    win_pct = (
        total_wins / (total_wins + total_losses)
        if (total_wins + total_losses) > 0
        else 0.0
    )

    # Playoff appearances and runner-up detection
    playoff_seasons: set[str] = set()
    runner_up_seasons: set[str] = set()
    for m in owner_matchups:
        if m.get("playoff_tier_type") != "WINNERS_BRACKET":
            continue
        season = str(m["season"])
        playoff_seasons.add(season)
        if m.get("playoff_round") == "Finals":
            own_team_id = (
                str(m["team_a_id"])
                if str(m.get("team_a_primary_owner_id")) == owner_id
                else str(m["team_b_id"])
            )
            if str(m.get("loser", "")) == own_team_id:
                runner_up_seasons.add(season)

    # Career high score (single game)
    owner_scores = [
        float(m["team_a_score"])
        if str(m.get("team_a_primary_owner_id")) == owner_id
        else float(m["team_b_score"])
        for m in owner_matchups
    ]
    high_score = max(owner_scores) if owner_scores else 0.0

    # Season-by-season table
    season_lines = ["Season | Team | Record | Avg PF/wk | Season High | Result"]
    season_lines.append("-" * 85)
    for row in sorted(owner_standings, key=lambda r: str(r["season"])):
        season_str = str(row["season"])
        is_champion = row.get("champion") == "Yes"
        is_runner_up = season_str in runner_up_seasons
        made_playoffs = season_str in playoff_seasons

        if is_champion:
            result = "CHAMPION"
        elif is_runner_up:
            result = "Runner-up"
        elif made_playoffs:
            result = "Playoffs"
        else:
            result = "Missed Playoffs"

        season_scores = [
            float(m["team_a_score"])
            if str(m.get("team_a_primary_owner_id")) == owner_id
            else float(m["team_b_score"])
            for m in owner_matchups
            if str(m["season"]) == season_str
        ]
        season_high = max(season_scores) if season_scores else 0.0

        season_lines.append(
            f"{season_str} | {row['team_name']} | {row['record']} | "
            f"{float(row['avg_pf']):.2f} | {season_high:.2f} | {result}"
        )

    # Head-to-head rivalry stats
    rival_map: dict[str, dict] = {}
    for m in owner_matchups:
        is_team_a = str(m.get("team_a_primary_owner_id")) == owner_id
        opp_id = (
            str(m["team_b_primary_owner_id"])
            if is_team_a
            else str(m["team_a_primary_owner_id"])
        )
        if opp_id not in all_owner_usernames:
            continue
        own_score = float(m["team_a_score"]) if is_team_a else float(m["team_b_score"])
        opp_score = float(m["team_b_score"]) if is_team_a else float(m["team_a_score"])

        if opp_id not in rival_map:
            rival_map[opp_id] = {
                "w": 0,
                "l": 0,
                "total_for": 0.0,
                "total_against": 0.0,
                "count": 0,
            }
        r = rival_map[opp_id]
        r["count"] += 1
        r["total_for"] += own_score
        r["total_against"] += opp_score
        if own_score > opp_score:
            r["w"] += 1
        elif own_score < opp_score:
            r["l"] += 1

    rival_lines = ["Opponent | W-L | Win% | Avg For | Avg Against | Avg Margin"]
    rival_lines.append("-" * 80)
    for opp_id, data in sorted(
        rival_map.items(), key=lambda x: -(x[1]["w"] + x[1]["l"])
    )[:10]:
        opp_name = all_owner_usernames.get(opp_id, opp_id)
        total = data["w"] + data["l"]
        h2h_win_pct = data["w"] / total if total > 0 else 0.0
        avg_for = data["total_for"] / data["count"] if data["count"] > 0 else 0.0
        avg_against = (
            data["total_against"] / data["count"] if data["count"] > 0 else 0.0
        )
        rival_lines.append(
            f"{opp_name} | {data['w']}-{data['l']} | {h2h_win_pct:.3f} | "
            f"{avg_for:.2f} | {avg_against:.2f} | {avg_for - avg_against:+.2f}"
        )

    num_seasons = len(owner_standings)
    prompt = (
        f"You are a fantasy football analyst with the wit of a late-night comedian and the "
        f"insight of a seasoned sports writer. Be funny and roast-y — ground every joke in "
        f"the actual data. Do not use headers, titles, or bullet points. Do not begin with a "
        f"title or heading of any kind. Write in flowing prose only, with a blank line between "
        f"each paragraph.\n\n"
        f"Write exactly 3 paragraphs as a career retrospective for {owner_username}, "
        f"who has played {num_seasons} season(s) in this fantasy league.\n\n"
        f"Paragraph 1 — Career Overview: Summarize their all-time record "
        f"({total_wins}-{total_losses}, {win_pct:.3f} win%), {championships} championship(s) "
        f"out of {num_seasons} seasons, {len(playoff_seasons)} playoff appearance(s), and "
        f"scoring profile (avg {avg_pf:.2f} pts/wk, career high {high_score:.2f}). "
        f"Were they a dynasty, a perennial contender, or a lovable bottom-feeder?\n\n"
        f"Paragraph 2 — Best and Worst Seasons: Highlight their standout season(s) and most "
        f"forgettable one(s). Ground every observation in the actual data — record, scoring, result.\n\n"
        f"Paragraph 3 — Rivalries: Talk about their notable head-to-head matchups. "
        f"Who do they dominate (win% ≥ 0.650)? Who is their nemesis (win% < 0.400)? "
        f"Any particularly evenly-contested rivalries?\n\n"
        f"Career Season-by-Season:\n{chr(10).join(season_lines)}\n\n"
        f"Head-to-Head Records (all matchups):\n{chr(10).join(rival_lines)}\n\n"
        "Write the career retrospective now:"
    )
    return prompt


async def generate_manager_recaps(
    table,
    api_key: str,
    pk: str,
    all_standings_rows: list[dict],
    all_matchups_rows: list[dict],
) -> None:
    """
    Generate and store AI career recaps for all managers in the league.

    Uses all-time standings and matchup data to build career summaries covering
    record, championships, playoff appearances, and head-to-head rivalries.
    Always overwrites any existing recap item.

    Args:
        table: A boto3 DynamoDB Table resource.
        api_key: The Anthropic API key.
        pk: The DynamoDB partition key (e.g., "LEAGUE#abc123").
        all_standings_rows: All standings rows across all seasons.
        all_matchups_rows: All matchup rows across all seasons.
    """
    client = AsyncAnthropic(api_key=api_key)

    all_owner_usernames: dict[str, str] = {}
    owner_standings_map: dict[str, list[dict]] = defaultdict(list)
    for row in all_standings_rows:
        owner_id = str(row["owner_id"])
        all_owner_usernames[owner_id] = str(row["owner_username"])
        owner_standings_map[owner_id].append(row)

    owner_matchups_map: dict[str, list[dict]] = defaultdict(list)
    for m in all_matchups_rows:
        a_owner = str(m.get("team_a_primary_owner_id", ""))
        b_owner = str(m.get("team_b_primary_owner_id", ""))
        if a_owner:
            owner_matchups_map[a_owner].append(m)
        if b_owner:
            owner_matchups_map[b_owner].append(m)

    prompts: dict[str, str] = {}
    for owner_id, standings_rows in owner_standings_map.items():
        prompts[owner_id] = build_manager_recap_prompt(
            owner_id=owner_id,
            owner_username=all_owner_usernames[owner_id],
            owner_standings=standings_rows,
            owner_matchups=owner_matchups_map.get(owner_id, []),
            all_owner_usernames=all_owner_usernames,
        )

    owner_ids = list(prompts.keys())
    if not owner_ids:
        return

    logger.info("Generating AI manager recaps for %d owners", len(owner_ids))
    results = await asyncio.gather(
        *[
            generate_single_recap(client, owner_id, prompts[owner_id])
            for owner_id in owner_ids
        ],
        return_exceptions=True,
    )

    for owner_id, result in zip(owner_ids, results):
        if isinstance(result, Exception):
            logger.error(
                "Failed to generate manager recap for owner %s: %s", owner_id, result
            )
            continue
        table.put_item(
            Item={
                "PK": pk,
                "SK": f"AI_RECAP#MANAGER#{owner_id}",
                "data": [
                    {
                        "owner_id": owner_id,
                        "owner_username": all_owner_usernames[owner_id],
                        "recap_text": result["recap_text"],
                        "generated_at": result["generated_at"],
                    }
                ],
            }
        )
        logger.info("Stored AI manager recap for owner %s", owner_id)
