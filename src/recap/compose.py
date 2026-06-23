"""Recap orchestrator (BE-022): AI generation + numeric validation.

``handler.py`` imports ``generate_recap`` and ``RecapGenerationError`` from here and
is agnostic to how the prose is produced. For one week's deterministic highlights:

1. ``ai_generate.generate`` — Amazon Bedrock (Nova Premier) writes the recap as a
   sports-newspaper-style column, constrained by a hard numeric guardrail.
2. ``validate.validate_recap`` — rejects any recap that prints a number the facts
   don't contain (a hallucinated score / stat).

There is **no deterministic fallback**: on any AI failure (blocked / empty /
unparseable / throttled) or a failed validation, ``RecapGenerationError`` propagates
and ``handler.py`` records the week as failed (failure_code ``RECAP``) so a later
retry regenerates it. The returned dict carries the Bedrock ``model`` id that
produced it.
"""

import ai_generate
import validate as validate_mod
from common.logging_utils import logger

# Re-exported so `handler.py`'s `except RecapGenerationError` catches both an AI
# failure and a validation rejection (raised below).
RecapGenerationError = ai_generate.RecapGenerationError
MODEL_ID = ai_generate.MODEL_ID


def generate_recap(highlights: dict, season: str, week: str) -> dict:
    """Generate one week's validated recap.

    Args:
        highlights: The deterministic highlights dict (see ``compute_highlights``).
        season: Season year (error context).
        week: Week number.

    Returns:
        ``{"headline": str, "body": str, "model": str}`` — ``model`` is the Bedrock
        model id that produced the recap.

    Raises:
        RecapGenerationError: The week has no matchups, the model failed or was
            blocked, or the output printed a number not present in the highlights.
    """
    if not highlights.get("matchups"):
        raise RecapGenerationError(f"No matchups to recap for {season} week {week}")

    recap = ai_generate.generate(highlights, season, week)
    if not validate_mod.validate_recap(recap, highlights):
        logger.warning(
            "AI recap failed numeric validation for %s week %s; leaving un-recapped",
            season,
            week,
        )
        raise RecapGenerationError(
            f"Recap failed numeric validation for {season} week {week}"
        )

    return {
        "headline": recap["headline"],
        "body": recap["body"],
        "model": ai_generate.MODEL_ID,
    }
