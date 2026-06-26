"""Unit tests for the Anthropic recap helper (BE-022)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import common.recap_llm as recap_llm


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Set the model env var and reset the lazily-built client between tests."""
    monkeypatch.setenv("RECAP_MODEL_ID", "claude-haiku-4-5")
    recap_llm._client = None
    yield
    recap_llm._client = None


def _block(text: str):
    return SimpleNamespace(type="text", text=text)


def _response(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(content=[_block(text)], stop_reason=stop_reason)


class TestGenerateRecap:
    def test_calls_model_with_messages_and_parses(self):
        client = MagicMock()
        client.messages.create.return_value = _response(
            "The Headline\n\nFirst para.\n\n\n\nSecond para.\n"
        )
        highlights = {"season": "2024", "week": 1, "matchups": []}
        with patch.object(recap_llm, "_client", client):
            result = recap_llm.generate_recap(highlights)

        assert result == {
            "headline": "The Headline",
            "body": "First para.\n\nSecond para.",
        }
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5"
        assert kwargs["max_tokens"] == recap_llm._MAX_GEN_LEN
        assert kwargs["temperature"] == recap_llm._TEMPERATURE
        assert kwargs["system"] == recap_llm._SYSTEM_PROMPT
        assert kwargs["messages"][0]["role"] == "user"
        assert json.loads(kwargs["messages"][0]["content"]) == highlights

    def test_truncated_max_tokens_still_returns(self):
        client = MagicMock()
        client.messages.create.return_value = _response(
            "Title\n\nBody.", stop_reason="max_tokens"
        )
        with patch.object(recap_llm, "_client", client):
            assert recap_llm.generate_recap({}) == {
                "headline": "Title",
                "body": "Body.",
            }

    def test_empty_text_raises(self):
        client = MagicMock()
        client.messages.create.return_value = _response("   ", stop_reason="end_turn")
        with patch.object(recap_llm, "_client", client):
            with pytest.raises(RuntimeError):
                recap_llm.generate_recap({})

    def test_no_text_block_raises(self):
        client = MagicMock()
        client.messages.create.return_value = SimpleNamespace(
            content=[], stop_reason="refusal"
        )
        with patch.object(recap_llm, "_client", client):
            with pytest.raises(RuntimeError):
                recap_llm.generate_recap({})

    def test_api_error_propagates(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("rate limited")
        with patch.object(recap_llm, "_client", client):
            with pytest.raises(RuntimeError, match="rate limited"):
                recap_llm.generate_recap({})


class TestGetClient:
    def test_builds_client_from_ssm_key_once(self):
        fake_sdk = MagicMock()
        with (
            patch.object(recap_llm, "anthropic", fake_sdk),
            patch.object(
                recap_llm, "get_secret_from_env_param", return_value="sk-test"
            ) as get_key,
        ):
            first = recap_llm._get_client()
            second = recap_llm._get_client()

        assert first is second  # cached
        get_key.assert_called_once_with("ANTHROPIC_API_KEY_SSM_PARAM")
        fake_sdk.Anthropic.assert_called_once()
        assert fake_sdk.Anthropic.call_args.kwargs["api_key"] == "sk-test"
        assert (
            fake_sdk.Anthropic.call_args.kwargs["max_retries"] == recap_llm._MAX_RETRIES
        )


class TestParseRecap:
    def test_leading_blank_lines_before_headline(self):
        assert recap_llm._parse_recap("\n\n  Title  \n\nBody.") == {
            "headline": "Title",
            "body": "Body.",
        }

    def test_only_headline(self):
        assert recap_llm._parse_recap("Just a headline") == {
            "headline": "Just a headline",
            "body": "",
        }

    def test_empty(self):
        assert recap_llm._parse_recap("") == {"headline": "", "body": ""}

    def test_system_prompt_includes_fact_fidelity_guardrail(self):
        assert "chris_j" in recap_llm._SYSTEM_PROMPT
        assert "Never invent" in recap_llm._SYSTEM_PROMPT

    def test_system_prompt_playoff_headline_rule(self):
        prompt = recap_llm._SYSTEM_PROMPT
        assert "WINNER'S BRACKET" in prompt
        assert "playoff_round" in prompt
        assert "Winners Consolation" in prompt
        assert "Losers Bracket" in prompt
