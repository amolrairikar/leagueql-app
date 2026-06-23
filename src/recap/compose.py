"""Recap orchestrator (BE-022): outline → AI → validate → snippet fallback.

``handler.py`` imports ``generate_recap`` and ``RecapGenerationError`` from here and
is agnostic to how the prose is produced. For one week's deterministic highlights:

1. ``outline.build_outline`` — a deterministic story plan (order + emphasis).
2. ``ai_generate.generate`` — Amazon Bedrock (Nova Premier) writes the column at
   temperature 0, constrained by the outline + a hard numeric guardrail.
3. ``validate.validate_recap`` — rejects any recap that prints a number the facts
   don't contain.
4. On **any** AI failure (blocked / empty / unparseable / throttled) or a failed
   validation, fall back to ``generate.generate_recap`` — the deterministic snippet
   composer (kept unchanged) — so a recap always exists.

The returned dict carries the ``model`` that actually produced it (the Bedrock
model id for an AI recap, ``snippet-v1`` for a fallback) so each recap is traceable.

``RecapGenerationError`` re-exported here is the snippet composer's — it is raised
only when even the fallback can't compose a week (no matchups), which ``handler.py``
counts as a failed week.
"""

import ai_generate
import generate as snippet
import outline as outline_mod
import validate as validate_mod
from common.logging_utils import logger

# Re-export the snippet composer's error so `handler.py`'s `except RecapGenerationError`
# catches the only failure that can escape `generate_recap` (a week with no matchups).
RecapGenerationError = snippet.RecapGenerationError


def generate_recap(highlights: dict, season: str, week: str) -> dict:
    """Compose one week's recap, preferring AI prose with a deterministic fallback.

    Args:
        highlights: The deterministic highlights dict (see ``compute_highlights``).
        season: Season year (seeds the fallback / error context).
        week: Week number.

    Returns:
        ``{"headline": str, "body": str, "model": str}`` — ``model`` is the Bedrock
        model id when the AI recap was used, else ``snippet-v1``.

    Raises:
        RecapGenerationError: Even the snippet fallback could not compose the week
            (no matchups). Propagated for ``handler.py`` to mark the week failed.
    """
    if highlights.get("matchups"):
        try:
            plan = outline_mod.build_outline(highlights)
            recap = ai_generate.generate(highlights, plan, season, week)
            if validate_mod.validate_recap(recap, highlights):
                return {
                    "headline": recap["headline"],
                    "body": recap["body"],
                    "model": ai_generate.MODEL_ID,
                }
            logger.warning(
                "AI recap failed numeric validation for %s week %s; "
                "falling back to snippet composer",
                season,
                week,
            )
        except Exception:
            # Any AI-side failure (blocked/empty/unparseable, throttling, transient
            # Bedrock errors) falls back to the deterministic composer rather than
            # losing the week.
            logger.warning(
                "AI recap generation failed for %s week %s; "
                "falling back to snippet composer",
                season,
                week,
                exc_info=True,
            )

    # Deterministic fallback. Raises RecapGenerationError only if the week has no
    # matchups to write about.
    fallback = snippet.generate_recap(highlights, season, week)
    return {
        "headline": fallback["headline"],
        "body": fallback["body"],
        "model": snippet.MODEL_ID,
    }
