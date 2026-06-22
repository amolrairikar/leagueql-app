"""Tests for ai_recap/generate.py with the Bedrock Converse client mocked."""

import json
from unittest.mock import MagicMock

import pytest


def _response(text=None, stop_reason="end_turn"):
    """Build a Bedrock Converse-shaped response (``converse`` return value)."""
    content = [] if text is None else [{"text": text}]
    return {
        "stopReason": stop_reason,
        "output": {"message": {"content": content}},
    }


@pytest.fixture
def mock_client(ai_recap_generate, monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(ai_recap_generate, "_client", client)
    return client


class TestGenerateRecap:
    def test_success_returns_headline_and_body(self, ai_recap_generate, mock_client):
        mock_client.converse.return_value = _response(
            json.dumps({"headline": "Big Week", "body": "Alice rolled."})
        )
        result = ai_recap_generate.generate_recap({"week": "1"}, "2025", "1")
        assert result == {"headline": "Big Week", "body": "Alice rolled."}

        # Model id + system prompt + highlights in the user turn (Converse shape).
        kwargs = mock_client.converse.call_args.kwargs
        assert kwargs["modelId"] == ai_recap_generate.MODEL_ID
        assert "commissioner" in kwargs["system"][0]["text"].lower()
        assert kwargs["messages"][0]["role"] == "user"

    def test_strips_code_fences(self, ai_recap_generate, mock_client):
        fenced = '```json\n{"headline": "H", "body": "B"}\n```'
        mock_client.converse.return_value = _response(fenced)
        result = ai_recap_generate.generate_recap({}, "2025", "1")
        assert result == {"headline": "H", "body": "B"}

    @pytest.mark.parametrize("reason", ["content_filtered", "guardrail_intervened"])
    def test_blocked_stop_reason_raises(self, ai_recap_generate, mock_client, reason):
        mock_client.converse.return_value = _response(None, stop_reason=reason)
        with pytest.raises(ai_recap_generate.RecapGenerationError):
            ai_recap_generate.generate_recap({}, "2025", "1")

    def test_empty_text_raises(self, ai_recap_generate, mock_client):
        mock_client.converse.return_value = _response("   ")
        with pytest.raises(ai_recap_generate.RecapGenerationError):
            ai_recap_generate.generate_recap({}, "2025", "1")

    def test_unparseable_json_raises(self, ai_recap_generate, mock_client):
        mock_client.converse.return_value = _response("not json at all")
        with pytest.raises(ai_recap_generate.RecapGenerationError):
            ai_recap_generate.generate_recap({}, "2025", "1")

    def test_missing_key_raises(self, ai_recap_generate, mock_client):
        mock_client.converse.return_value = _response(
            json.dumps({"headline": "only headline"})
        )
        with pytest.raises(ai_recap_generate.RecapGenerationError):
            ai_recap_generate.generate_recap({}, "2025", "1")

    def test_blank_body_raises(self, ai_recap_generate, mock_client):
        mock_client.converse.return_value = _response(
            json.dumps({"headline": "Has headline", "body": "   "})
        )
        with pytest.raises(ai_recap_generate.RecapGenerationError):
            ai_recap_generate.generate_recap({}, "2025", "1")

    def test_get_client_constructs_once(self, ai_recap_generate, monkeypatch):
        # _get_client builds a bedrock-runtime client lazily and caches it.
        monkeypatch.setattr(ai_recap_generate, "_client", None)
        sentinel = MagicMock()
        ctor = MagicMock(return_value=sentinel)
        monkeypatch.setattr(ai_recap_generate.boto3, "client", ctor)
        assert ai_recap_generate._get_client() is sentinel
        assert ai_recap_generate._get_client() is sentinel
        ctor.assert_called_once()
        assert ctor.call_args.args[0] == "bedrock-runtime"
