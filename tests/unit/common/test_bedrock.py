"""Unit tests for the Bedrock recap helper (BE-022)."""

import json
from unittest.mock import MagicMock, patch

import pytest

import common.bedrock as bedrock


def _converse_response(text: str) -> dict:
    return {"output": {"message": {"content": [{"text": text}]}}}


@pytest.fixture(autouse=True)
def _model_env(monkeypatch):
    monkeypatch.setenv(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )


class TestGenerateRecap:
    def test_calls_converse_with_model_and_highlights(self):
        client = MagicMock()
        client.converse.return_value = _converse_response("Headline\n\nBody para.")
        highlights = {"season": "2024", "week": 1, "matchups": []}
        with patch.object(bedrock, "_bedrock_client", client):
            result = bedrock.generate_recap(highlights)

        kwargs = client.converse.call_args.kwargs
        assert kwargs["modelId"] == "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        assert kwargs["system"][0]["text"]  # voice + guardrail present
        assert json.loads(kwargs["messages"][0]["content"][0]["text"]) == highlights
        assert kwargs["inferenceConfig"]["maxTokens"] == 2000
        assert result == {"headline": "Headline", "body": "Body para."}

    def test_system_prompt_includes_fact_fidelity_guardrail(self):
        # The name/fact-fidelity guardrail must be in the system prompt.
        assert "chris_j" in bedrock._SYSTEM_PROMPT
        assert "Never invent" in bedrock._SYSTEM_PROMPT

    def test_multi_paragraph_body_is_normalized(self):
        client = MagicMock()
        client.converse.return_value = _converse_response(
            "The Headline\n\nFirst para.\n\n\n\nSecond para.\n"
        )
        with patch.object(bedrock, "_bedrock_client", client):
            result = bedrock.generate_recap({})
        assert result["headline"] == "The Headline"
        assert result["body"] == "First para.\n\nSecond para."

    def test_leading_blank_lines_before_headline(self):
        client = MagicMock()
        client.converse.return_value = _converse_response("\n\n  Title  \n\nBody.")
        with patch.object(bedrock, "_bedrock_client", client):
            result = bedrock.generate_recap({})
        assert result["headline"] == "Title"
        assert result["body"] == "Body."


class TestParsing:
    def test_extract_text_joins_blocks(self):
        resp = {"output": {"message": {"content": [{"text": "a"}, {"text": "b"}]}}}
        assert bedrock._extract_text(resp) == "ab"

    def test_extract_text_empty_logs_and_returns_empty(self):
        assert bedrock._extract_text({"output": {"message": {"content": []}}}) == ""

    def test_parse_recap_only_headline(self):
        assert bedrock._parse_recap("Just a headline") == {
            "headline": "Just a headline",
            "body": "",
        }

    def test_parse_recap_empty(self):
        assert bedrock._parse_recap("") == {"headline": "", "body": ""}
