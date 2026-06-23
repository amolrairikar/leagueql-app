"""LLM recap generation via Amazon Bedrock — Amazon Nova Premier (BE-022).

The only LLM-touching code in the recap pipeline. Calls Bedrock's **Converse**
API with the boto3 ``bedrock-runtime`` client, authenticating with the Lambda's
IAM execution role (SigV4) — there is **no API-key secret**. Inputs are the
deterministic ``highlights`` dict (``highlights.py`` — the numeric guardrail) and
the deterministic ``outline`` (``outline.py`` — the story plan / order). Output is
``{headline, body}``.

The system prompt carries the persona / voice / output contract / numeric
guardrail; the highlights + outline ride in the user turn (data belongs in the
user message, never the system prompt). Generation runs at **temperature 0** so a
given week's prose stays stable within a run. ``compose.py`` wraps this with a
numeric-validation gate and a deterministic snippet fallback, so a blocked or
unusable response never loses the week.

Model + provider: Amazon Nova Premier on Amazon Bedrock. The model /
inference-profile id is supplied via ``BEDROCK_MODEL_ID`` (default the cross-region
Nova Premier inference profile) so a region-specific profile can be set without a
code change.
"""

import json
import os

import boto3
import botocore.config

from common.logging_utils import logger

# Bedrock model id. Defaults to the cross-region Nova Premier inference profile
# (Nova Premier is served on-demand via an inference profile). Overridable via env
# so a region-specific profile id can be supplied without a code change.
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-premier-v1:0")

# Headroom for a headline + a multi-paragraph column.
MAX_TOKENS = 2000

# Converse ``stopReason`` values that mean the model declined / was filtered
# rather than completing — treat like a refusal so the week falls back.
_BLOCKED_STOP_REASONS = {"content_filtered", "guardrail_intervened"}

_SYSTEM_PROMPT = (
    "You are the commissioner of a fantasy football league writing the weekly "
    "recap column — a lively, cohesive 'commissioner's column' that flows as one "
    "narrative about the week: its storylines, upsets, standout performances, and "
    "a little good-natured trash talk. Write 3-5 short connected paragraphs (not a "
    "list of separate game summaries), refer to managers and teams by name, and "
    "land a fun, opinionated voice.\n\n"
    "You will be given the week's FACTS (every legal number and name) and an "
    "OUTLINE (the order to cover matchups in, the headline angle, and the beats "
    "worth hitting). Follow the outline's ordering and emphasis; lead with the "
    "biggest story.\n\n"
    "CRITICAL GUARDRAIL: Use ONLY the numbers, names, and facts provided. Never "
    "invent, estimate, or alter any score, player, statistic, margin, or record. "
    "If a detail is not in the provided data, do not mention it.\n\n"
    "Respond with ONLY a JSON object (no markdown, no code fences) of the exact "
    'shape: {"headline": "<short punchy headline>", "body": "<the recap '
    'narrative, paragraphs separated by blank lines>"}.'
)


class RecapGenerationError(Exception):
    """Raised when the model is filtered or returns unusable output for a week.

    ``compose.py`` catches this and falls back to the deterministic snippet
    composer so the week is still recapped.
    """


_retry_config = botocore.config.Config(retries={"mode": "standard"})

# Module-level client; constructed lazily so importing this module never requires
# AWS credentials (tests patch ``_client`` / monkeypatch the factory).
_client = None


def _get_client():
    global _client
    if _client is None:
        # Region is read from AWS_REGION (set automatically in Lambda); no API key.
        _client = boto3.client("bedrock-runtime", config=_retry_config)
    return _client


def _strip_code_fences(text: str) -> str:
    """Strip a leading/trailing ```...``` fence if the model wrapped its JSON.

    The system prompt asks for raw JSON, but a model occasionally wraps it; this
    keeps a stray fence from failing the parse without masking truly bad output.
    """
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def generate(highlights: dict, outline: dict, season: str, week: str) -> dict:
    """Generate a ``{headline, body}`` recap for one week via Bedrock.

    Args:
        highlights: The deterministic highlights dict (the numeric guardrail).
        outline: The deterministic story plan (see ``build_outline``).
        season: Season year (for logging / error context).
        week: Week number (for logging / error context).

    Returns:
        ``{"headline": str, "body": str}``.

    Raises:
        RecapGenerationError: The model was content-filtered / guardrail-blocked
            or returned output that could not be parsed into the contract.
    """
    client = _get_client()
    user_text = (
        f"Write the recap for season {season}, week {week}.\n\n"
        "FACTS (use only these numbers and names):\n"
        + json.dumps(highlights, separators=(",", ":"))
        + "\n\nOUTLINE (cover matchups in this order, hit these beats):\n"
        + json.dumps(outline, separators=(",", ":"))
    )
    response = client.converse(
        modelId=MODEL_ID,
        system=[{"text": _SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_text}]}],
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0},
    )

    # Content filtering / guardrail intervention surface as a stopReason (HTTP 200),
    # not an exception — check before reading content so the week falls back.
    stop_reason = response.get("stopReason")
    if stop_reason in _BLOCKED_STOP_REASONS:
        logger.warning(
            "Recap generation blocked (%s) for season=%s week=%s",
            stop_reason,
            season,
            week,
        )
        raise RecapGenerationError(
            f"Model blocked recap for {season} week {week} ({stop_reason})"
        )

    blocks = response.get("output", {}).get("message", {}).get("content", [])
    text = _strip_code_fences("".join(b.get("text", "") for b in blocks).strip())
    if not text:
        raise RecapGenerationError(f"Empty recap for {season} week {week}")

    try:
        parsed = json.loads(text)
        headline = str(parsed["headline"]).strip()
        body = str(parsed["body"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Unparseable recap for season=%s week=%s: %s", season, week, exc)
        raise RecapGenerationError(
            f"Unparseable recap for {season} week {week}"
        ) from exc

    if not headline or not body:
        raise RecapGenerationError(f"Incomplete recap for {season} week {week}")

    return {"headline": headline, "body": body}
