"""Shared Anthropic recap generation for LeagueQL (BE-022).

Vendored into the recap-generator container image. Recaps are produced **synchronously**
via the Anthropic Messages API (Claude Haiku 4.5, model ``RECAP_MODEL_ID`` =
``claude-haiku-4-5``) — one ``messages.create`` call per week's highlights. The caller
(``src/recap_generator``) paces calls under the account RPM ceiling; the SDK additionally
auto-retries ``429``/``5xx`` with exponential backoff.

This module owns the prompt, the synchronous call, and parsing the model's text back into
``{"headline", "body"}``. The voice + fact-fidelity guardrail (``_SYSTEM_PROMPT``) is the
one real gap observed in testing (the model fabricated manager surnames from usernames);
it is kept verbatim.
"""

import json
import os

from common.logging_utils import logger
from common.secrets import get_secret_from_env_param

# The SDK ships in the recap-generator container (requirements.txt). Guarded so this
# module still imports in environments without it (the SDK is only needed to actually
# generate — unit tests patch around it).
try:  # pragma: no cover - import shim
    import anthropic
except ImportError:  # pragma: no cover - import shim
    anthropic = None

# Voice + hard fact-fidelity guardrail. The guardrail is the one real gap observed in
# the model demo (it fabricated manager surnames from usernames); keeping it is
# worthwhile regardless of which model RECAP_MODEL_ID points at.
_SYSTEM_PROMPT = (
    "You are a fantasy football columnist writing a weekly matchup recap. Write a "
    "medium-long column in a lighthearted-but-journalistic voice: it should read "
    "like a real sports column, with playful roasts where they are deserved. "
    "Output a single headline on the first line, then a blank line, then the body as "
    "plain prose paragraphs separated by blank lines. Do NOT use markdown, bullet "
    "points, or headers in the body.\n\n"
    "THE HEADLINE — make it genuinely creative, the best line in the column:\n"
    "- Be witty and surprising. Reach for clever wordplay, puns, alliteration, or a "
    "vivid metaphor; a pop-culture or sports-history riff is welcome when it fits.\n"
    "- Hook it to the single most dramatic, funny, or lopsided thing that actually "
    "happened that week — the blowout, the nail-biter, the bench disaster, the "
    "upset.\n"
    "- Avoid generic, templated headlines. Never just 'Week N Recap' or "
    "'Team A beats Team B' — those are banned.\n"
    "- PLAYOFF WEEKS: when any matchup carries a 'playoff_round', anchor the headline "
    "to a WINNER'S BRACKET game — one whose 'playoff_round' is 'Quarterfinals', "
    "'Semifinals', or 'Finals' — and prefer the highest-stakes round present (Finals "
    "over Semifinals over Quarterfinals). NEVER build the headline around a "
    "consolation or losers-bracket game (a 'playoff_round' of 'Winners Consolation' "
    "or 'Losers Bracket'); those may still feature in the body, but the championship "
    "chase leads.\n"
    "- Keep it punchy (roughly 4-12 words) and still grounded: the cleverness must "
    "come from the real events, never from invented facts.\n\n"
    "STRICT FACT FIDELITY — this is mandatory:\n"
    "- Use the team and manager/display names EXACTLY as provided. Never expand, "
    "guess, or invent a real name. A username like 'chris_j' must stay 'Chris' or "
    "'chris_j' — never 'Chris Johnson'.\n"
    "- Never invent statistics, scores, players, injuries, transactions, or events "
    "that are not present in the provided highlights. Every number, player, and "
    "outcome you mention must trace directly to the input.\n"
    "- You MAY state obvious deductions that follow from the data (e.g. that the two "
    "semifinal winners will meet in the final). That is not fabrication.\n"
    "If a detail is not in the highlights, leave it out."
)

# Cap output so a single recap stays bounded (and cheap) regardless of how many
# matchups a week has, and a mild temperature for headline creativity. Haiku 4.5 still
# accepts ``temperature`` (it is not in the Opus-4.7+/Fable family that rejects it).
_MAX_GEN_LEN = 2000
_TEMPERATURE = 0.7

# Generous retry budget: the account's ~50 RPM ceiling makes transient 429s likely under
# a backlog, and the SDK backs off + honors Retry-After. The caller still paces calls.
_MAX_RETRIES = 4

# Built lazily on first use so this module imports without the SDK, and so the client is
# constructed after the recap-generator installs OTel httpx instrumentation (BE-021).
_client = None


def _get_client():
    """Return the cached Anthropic client, building it from the SSM-stored key once.

    The API key is a SecureString SSM parameter named by ``ANTHROPIC_API_KEY_SSM_PARAM``
    (same pattern as the Stripe/Axiom secrets — never in env/TF state/CI).
    """
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            api_key=get_secret_from_env_param("ANTHROPIC_API_KEY_SSM_PARAM"),
            max_retries=_MAX_RETRIES,
        )
    return _client


def generate_recap(highlights: dict) -> dict:
    """Generate one week's recap synchronously and parse it into ``{headline, body}``.

    Args:
        highlights: A JSON-serializable dict describing the week (season, week, playoff
            round if any, and each matchup's teams/records/scores/top performers).

    Returns:
        ``{"headline": str, "body": str}``.

    Raises:
        Exception: On an empty/refused response, or after the SDK exhausts its retries
            on a ``429``/``5xx``. The caller leaves the league's marker pending so the
            next scheduled run retries.
    """
    response = _get_client().messages.create(
        model=os.environ["RECAP_MODEL_ID"],
        max_tokens=_MAX_GEN_LEN,
        temperature=_TEMPERATURE,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(highlights)}],
    )
    if response.stop_reason == "max_tokens":
        # Truncated but usable; _MAX_GEN_LEN is generous for one column, so keep it.
        logger.warning("Recap hit max_tokens; body may be truncated")

    text = next(
        (block.text for block in response.content if block.type == "text"), ""
    ).strip()
    if not text:
        # Empty content (e.g. a pre-output refusal) — fail so the marker stays pending.
        raise RuntimeError(
            f"Anthropic returned no recap text (stop_reason={response.stop_reason})"
        )
    return _parse_recap(text)


def _parse_recap(text: str) -> dict:
    """Split the model output into a headline (first non-empty line) and body."""
    lines = text.split("\n")
    headline = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip():
            headline = line.strip()
            body_start = i + 1
            break

    # Re-join the remainder and normalize paragraph spacing to single blank lines.
    remainder = "\n".join(lines[body_start:]).strip()
    paragraphs = [p.strip() for p in remainder.split("\n\n") if p.strip()]
    body = "\n\n".join(paragraphs)
    return {"headline": headline, "body": body}
