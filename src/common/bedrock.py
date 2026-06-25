"""Shared AWS Bedrock recap generation for LeagueQL (BE-022).

Vendored into the recap-drainer + recap-completion Lambda zips. Recaps are produced
via Bedrock **batch inference** (asynchronous ``CreateModelInvocationJob``), which
runs on a separate service-quota lane from on-demand throughput and so sidesteps the
very low real-time requests-per-minute quota for Meta Llama 3.3 70B Instruct. This
module owns three things: building a single batch **input record** from a week's
highlights, submitting a batch job, and parsing a batch **output record** back into
a recap.

Batch input/output uses **InvokeModel-style** ``modelInput``/``modelOutput``, not the
Converse API, so this module formats the model-native request body (the Llama-3
instruct prompt template) and reads the model-native response. The model is
parameterized by ``BEDROCK_MODEL_ID`` (currently Meta Llama 3.3 70B Instruct via its
US cross-region inference profile, ``us.meta.llama3-3-70b-instruct-v1:0`` — the bare
foundation-model ID is inference-profile-only and rejects on-demand throughput).
Because batch is not model-agnostic, swapping models means updating the prompt/body
format here, not just the env var.
"""

import json
import os

import boto3

from common.logging_utils import logger

# Control-plane client for batch job submission (``create_model_invocation_job`` lives
# on ``bedrock``, not ``bedrock-runtime``). Batch carries its own quota, so there is no
# client-side rate limiter here.
_bedrock_client = boto3.client("bedrock")

# Voice + hard fact-fidelity guardrail. The guardrail is the one real gap observed in
# the model demo (it fabricated manager surnames from usernames); keeping it is
# worthwhile regardless of which model BEDROCK_MODEL_ID points at.
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
# matchups a week has, and a mild temperature for headline creativity.
_MAX_GEN_LEN = 2000
_TEMPERATURE = 0.7


def _format_llama_prompt(system: str, user: str) -> str:
    """Wrap system + user text in the Llama-3 instruct chat template.

    Converse handled this for us; batch InvokeModel does not, so we build the native
    prompt string the model was trained on. If ``BEDROCK_MODEL_ID`` ever points at a
    non-Llama model, this template must change with it.
    """
    return (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{system}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
        f"{user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    )


def _model_input(highlights: dict) -> dict:
    """The model-native InvokeModel request body for one week's highlights."""
    return {
        "prompt": _format_llama_prompt(_SYSTEM_PROMPT, json.dumps(highlights)),
        "max_gen_len": _MAX_GEN_LEN,
        "temperature": _TEMPERATURE,
    }


def build_recap_record(record_id: str, highlights: dict) -> dict:
    """Build one batch-inference JSONL record for a week's recap.

    Args:
        record_id: An opaque per-record id (alphanumeric, >= 11 chars — Bedrock's
            constraint) that the drainer maps back to ``(league, season, week)`` in
            the job manifest. The output JSONL echoes it.
        highlights: A JSON-serializable dict describing the week (season, week,
            playoff round if any, and each matchup's teams/records/scores/top
            performers).

    Returns:
        ``{"recordId": str, "modelInput": dict}`` — one line of the batch input JSONL.
    """
    return {"recordId": record_id, "modelInput": _model_input(highlights)}


def submit_batch_job(
    *, job_name: str, input_uri: str, output_uri: str, role_arn: str
) -> str:
    """Submit a Bedrock batch inference job over an input JSONL already in S3.

    Args:
        job_name: A unique job name.
        input_uri: ``s3://…/input/<job>.jsonl`` holding the ``build_recap_record``
            lines.
        output_uri: ``s3://…/output/<job>/`` prefix Bedrock writes results under.
        role_arn: The Bedrock batch **service role** (trust ``bedrock.amazonaws.com``)
            Bedrock assumes to read the input and write the output.

    Returns:
        The created job's ARN (used as the manifest key / completion-event match).
    """
    model_id = os.environ["BEDROCK_MODEL_ID"]
    resp = _bedrock_client.create_model_invocation_job(
        jobName=job_name,
        roleArn=role_arn,
        modelId=model_id,
        inputDataConfig={"s3InputDataConfig": {"s3Uri": input_uri}},
        outputDataConfig={"s3OutputDataConfig": {"s3Uri": output_uri}},
    )
    job_arn = resp["jobArn"]
    logger.info("Submitted Bedrock batch job %s (%s)", job_name, job_arn)
    return job_arn


def parse_recap_output(model_output: dict) -> dict:
    """Parse a batch ``modelOutput`` record into ``{"headline", "body"}``.

    ``model_output`` is the model-native InvokeModel response (for Llama: a dict with
    a ``generation`` string). ``body`` joins paragraphs with ``\\n\\n`` and has no
    markdown; the headline is the model's first non-empty line.
    """
    text = (model_output.get("generation") or "").strip()
    if not text:
        logger.warning("Bedrock batch record returned no generation text")
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
