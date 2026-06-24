"""Shared AWS Bedrock recap generation for LeagueQL (BE-022).

Vendored into the recap-generator Lambda's deployment zip. Wraps a single
``bedrock-runtime`` client (mirroring ``common.sns`` / ``common.subscription``
style) and the Converse call that turns a week's matchup highlights into the
AI-written recap column.

The model is parameterized by the ``BEDROCK_MODEL_ID`` env var — the full versioned
Bedrock model ID as shown in the console, ``anthropic.claude-haiku-4-5-20251001-v1:0``
(the unversioned ``anthropic.claude-haiku-4-5`` is rejected as an invalid model
identifier), so swapping models is a one-line config change.
The client uses **adaptive** retry mode so Bedrock ``ThrottlingException`` backoff
is handled by botocore before a parallel batch ever sees an error.
"""

import json
import os

import boto3
import botocore.config

from common.logging_utils import logger

# Adaptive retry mode handles Bedrock throttling (RPM/TPM) backoff for us, which
# matters under the parallel multi-week backfill the recap Lambda runs.
_retry_config = botocore.config.Config(retries={"mode": "adaptive"})
_bedrock_client = boto3.client("bedrock-runtime", config=_retry_config)

# Voice + hard fact-fidelity guardrail. The guardrail is the one real gap observed
# in the model demo (it fabricated manager surnames from usernames); keeping it is
# worthwhile regardless of which model BEDROCK_MODEL_ID points at.
_SYSTEM_PROMPT = (
    "You are a fantasy football columnist writing a weekly matchup recap. Write a "
    "medium-long column in a lighthearted-but-journalistic voice: it should read "
    "like a real sports column, with playful roasts where they are deserved. "
    "Output a single punchy headline on the first line, then a blank line, then the "
    "body as plain prose paragraphs separated by blank lines. Do NOT use markdown, "
    "bullet points, or headers in the body.\n\n"
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
# matchups a week has.
_MAX_TOKENS = 2000


def generate_recap(highlights: dict) -> dict:
    """Generate one week's recap column from its matchup highlights.

    Args:
        highlights: A JSON-serializable dict describing the week (season, week,
            playoff round if any, and each matchup's teams/records/scores/top
            performers). Built by the recap Lambda from the precomputed views.

    Returns:
        ``{"headline": str, "body": str}`` — ``body`` is the prose with paragraphs
        joined by ``\\n\\n`` and no markdown. The headline is the model's first
        non-empty line; everything after it is the body.
    """
    model_id = os.environ["BEDROCK_MODEL_ID"]
    response = _bedrock_client.converse(
        modelId=model_id,
        system=[{"text": _SYSTEM_PROMPT}],
        messages=[
            {
                "role": "user",
                "content": [{"text": json.dumps(highlights)}],
            }
        ],
        inferenceConfig={"maxTokens": _MAX_TOKENS},
    )
    text = _extract_text(response)
    return _parse_recap(text)


def _extract_text(response: dict) -> str:
    """Pull the concatenated text out of a Converse response, tolerating shape."""
    blocks = response.get("output", {}).get("message", {}).get("content", [])
    parts = [b.get("text", "") for b in blocks if isinstance(b, dict)]
    text = "".join(parts).strip()
    if not text:
        logger.warning("Bedrock Converse returned no text content")
    return text


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
