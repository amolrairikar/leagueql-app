"""LLM recap generation via Amazon Bedrock — Amazon Nova Lite (BE-022).

The only LLM-touching code in the recap pipeline. Calls Bedrock's **Converse**
API with the boto3 ``bedrock-runtime`` client, authenticating with the Lambda's
IAM execution role (SigV4) — there is **no API-key secret** to source. Input is
the deterministic highlights dict from ``highlights.py``; output is
``{headline, body}``. The system prompt carries the persona / voice / output
contract / numeric guardrail; the highlights ride in the user turn (data belongs
in the user message, never the system prompt).

Model + provider: Amazon Nova Lite on Amazon Bedrock. The model /
inference-profile id is supplied via ``BEDROCK_MODEL_ID`` (default the bare Nova
Lite id) so a region-specific inference profile can be set without a code change.
"""

import json
import os

import boto3
import botocore.config

from common.logging_utils import logger

# Bedrock model id (the bare Nova Lite id). Overridable via env so a
# region-specific inference-profile id (e.g. ``us.amazon.nova-lite-v1:0``) can be
# supplied without a code change.
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")

# Headroom for a headline + a few-paragraph narrative.
MAX_TOKENS = 2000

# Converse ``stopReason`` values that mean the model declined / was filtered
# rather than completing — treat like a refusal so the week is left un-recapped.
_BLOCKED_STOP_REASONS = {"content_filtered", "guardrail_intervened"}

_SYSTEM_PROMPT = (
    "You are the commissioner of a fantasy football league writing the weekly "
    "recap column — a lively, witty 'commissioner's column' that captures the "
    "week's storylines, upsets, standout performances, and a little good-natured "
    "trash talk. Write in second/third person about the managers by name, keep it "
    "to 2-4 short paragraphs, and land a fun, opinionated voice.\n\n"
    "CRITICAL GUARDRAIL: Use ONLY the numbers, names, and facts provided in the "
    "user message. Never invent, estimate, or alter any score, player, statistic, "
    "or record. If a detail is not in the provided data, do not mention it.\n\n"
    "Respond with ONLY a JSON object (no markdown, no code fences) of the exact "
    'shape: {"headline": "<short punchy headline>", "body": "<the recap '
    'narrative>"}.'
)


class RecapGenerationError(Exception):
    """Raised when the model is filtered or returns unusable output for a week.

    The caller leaves that week un-recapped (no RECAP item written); a later retry
    fills it.
    """


_retry_config = botocore.config.Config(retries={"mode": "standard"})

# Module-level client; constructed lazily so importing this module never requires
# AWS credentials (unit tests patch ``_client`` / monkeypatch the factory).
_client = None


def _get_client():
    global _client
    if _client is None:
        # Region is read from AWS_REGION (set automatically in Lambda); no API key.
        _client = boto3.client("bedrock-runtime", config=_retry_config)
    return _client


def _strip_code_fences(text: str) -> str:
    """Strip a leading/trailing ```...``` fence if the model wrapped its JSON.

    The system prompt asks for raw JSON, but a smaller model occasionally wraps it;
    this keeps a stray fence from failing the parse without masking truly bad output.
    """
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def generate_recap(highlights: dict, season: str, week: str) -> dict:
    """Generate a ``{headline, body}`` recap for one week from its highlights.

    Args:
        highlights: The deterministic highlights dict (see ``compute_highlights``).
        season: Season year (for logging / error context).
        week: Week number (for logging / error context).

    Returns:
        ``{"headline": str, "body": str}``.

    Raises:
        RecapGenerationError: The model was content-filtered / guardrail-blocked
            or returned output that could not be parsed into the contract. The week
            is left un-recapped so a later retry can fill it.
    """
    client = _get_client()
    response = client.converse(
        modelId=MODEL_ID,
        system=[{"text": _SYSTEM_PROMPT}],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": (
                            f"Write the recap for season {season}, week {week}. "
                            "Here are this week's facts:\n\n"
                            + json.dumps(highlights, separators=(",", ":"))
                        )
                    }
                ],
            }
        ],
        inferenceConfig={"maxTokens": MAX_TOKENS},
    )

    # Content filtering / guardrail intervention surface as a stopReason (HTTP 200),
    # not an exception — check before reading content so the week is left un-recapped.
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
