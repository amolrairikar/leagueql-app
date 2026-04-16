import asyncio
from collections import defaultdict
from datetime import datetime

from anthropic import AsyncAnthropic
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

    header = "Rank | Owner | Team | Record | Avg PF | Avg PA | Win% | Win% vs League"
    divider = "-" * 75
    standings_lines = [header, divider]
    for rank, row in enumerate(standings_sorted, 1):
        standings_lines.append(
            f"{rank} | {row['owner_username']} | {row['team_name']} | "
            f"{row['record']} | {float(row['avg_pf']):.2f} | {float(row['avg_pa']):.2f} | "
            f"{float(row['win_pct']):.3f} | {float(row['win_pct_vs_league']):.3f}"
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

    prompt = (
        f"You are a fantasy football analyst. Write a 2-3 paragraph season recap for "
        f"the {season} fantasy football season.\n\n"
        "Cover: the champion and their performance, notable scoring leaders, interesting "
        "matchup moments, and the overall character of the season. Keep the tone engaging "
        "and conversational, as if writing for a league newsletter. Do not use headers or "
        "bullet points — write in flowing prose only.\n\n"
        f"Season Standings:\n{chr(10).join(standings_lines)}\n\n"
        f"Weekly Matchups:\n{chr(10).join(matchup_lines)}\n\n"
        "Write the recap now:"
    )
    return prompt


async def generate_single_recap(
    client: AsyncAnthropic,
    season: str,
    prompt: str,
) -> dict:
    """
    Call Claude to generate a recap for a single season.

    Args:
        client: An AsyncAnthropic client instance.
        season: The season year.
        prompt: The prompt to send to Claude.

    Returns:
        A dict with recap_text, generated_at, and season.
    """
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    content_block = message.content[0]
    if not isinstance(content_block, TextBlock):
        raise ValueError(f"Unexpected content block type: {type(content_block)}")
    return {
        "season": season,
        "recap_text": content_block.text,
        "generated_at": datetime.now().isoformat() + "Z",
    }


async def generate_recaps_for_all_seasons(
    table,
    api_key: str,
    pk: str,
    seasons: list[str],
    standings_by_season: dict[str, list[dict]],
    matchups_by_season: dict[str, list[dict]],
) -> None:
    """
    Generate and store AI recaps for all seasons that don't already have one.

    Checks DynamoDB before generating to avoid redundant API calls. Failures
    for individual seasons are logged and skipped without raising.

    Args:
        table: A boto3 DynamoDB Table resource.
        api_key: The Anthropic API key.
        pk: The DynamoDB partition key (e.g., "LEAGUE#abc123").
        seasons: List of seasons to potentially generate recaps for.
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
