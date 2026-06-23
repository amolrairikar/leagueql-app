"""Tests for recap/ai_generate.py — the Bedrock (Nova Premier) Converse call.

The bedrock-runtime client is mocked, so these assert the request shape (model id,
temperature 0, facts + outline in the user turn), JSON parsing (incl. fenced
output), and that filtered / empty / unparseable responses raise.
"""

from unittest.mock import MagicMock

import pytest


def _converse_response(text):
    return {
        "stopReason": "end_turn",
        "output": {"message": {"content": [{"text": text}]}},
    }


@pytest.fixture
def mock_client(recap_ai_generate, monkeypatch):
    client = MagicMock()
    client.converse.return_value = _converse_response(
        '{"headline": "Big Win", "body": "Aces rolled."}'
    )
    monkeypatch.setattr(recap_ai_generate, "_client", client)
    return client


_HIGHLIGHTS = {"season": "2025", "week": "1", "matchups": [{"margin": 10}]}
_OUTLINE = {"headline_angle": "general", "matchups": [{"winner": "Aces"}]}


class TestGenerate:
    def test_returns_parsed_recap(self, recap_ai_generate, mock_client):
        result = recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")
        assert result == {"headline": "Big Win", "body": "Aces rolled."}

    def test_request_shape(self, recap_ai_generate, mock_client):
        recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")
        kwargs = mock_client.converse.call_args.kwargs
        assert kwargs["modelId"] == recap_ai_generate.MODEL_ID
        assert kwargs["inferenceConfig"]["temperature"] == 0
        assert kwargs["inferenceConfig"]["maxTokens"] == recap_ai_generate.MAX_TOKENS
        # Persona/guardrail in the system turn; facts + outline in the user turn.
        assert "commissioner" in kwargs["system"][0]["text"].lower()
        user_text = kwargs["messages"][0]["content"][0]["text"]
        assert "FACTS" in user_text and "OUTLINE" in user_text
        assert '"general"' in user_text  # outline serialized in
        assert '"matchups"' in user_text

    def test_strips_code_fences(self, recap_ai_generate, mock_client):
        mock_client.converse.return_value = _converse_response(
            '```json\n{"headline": "H", "body": "B"}\n```'
        )
        result = recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")
        assert result == {"headline": "H", "body": "B"}

    def test_strips_bare_fence_without_language(self, recap_ai_generate, mock_client):
        mock_client.converse.return_value = _converse_response(
            '```{"headline": "H", "body": "B"}```'
        )
        result = recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")
        assert result == {"headline": "H", "body": "B"}

    @pytest.mark.parametrize(
        "stop_reason", ["content_filtered", "guardrail_intervened"]
    )
    def test_blocked_raises(self, recap_ai_generate, mock_client, stop_reason):
        resp = _converse_response('{"headline": "H", "body": "B"}')
        resp["stopReason"] = stop_reason
        mock_client.converse.return_value = resp
        with pytest.raises(recap_ai_generate.RecapGenerationError):
            recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")

    def test_empty_text_raises(self, recap_ai_generate, mock_client):
        mock_client.converse.return_value = _converse_response("")
        with pytest.raises(recap_ai_generate.RecapGenerationError):
            recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")

    def test_unparseable_json_raises(self, recap_ai_generate, mock_client):
        mock_client.converse.return_value = _converse_response("not json at all")
        with pytest.raises(recap_ai_generate.RecapGenerationError):
            recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")

    def test_missing_key_raises(self, recap_ai_generate, mock_client):
        mock_client.converse.return_value = _converse_response('{"headline": "H"}')
        with pytest.raises(recap_ai_generate.RecapGenerationError):
            recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")

    def test_blank_fields_raise(self, recap_ai_generate, mock_client):
        mock_client.converse.return_value = _converse_response(
            '{"headline": "  ", "body": "  "}'
        )
        with pytest.raises(recap_ai_generate.RecapGenerationError):
            recap_ai_generate.generate(_HIGHLIGHTS, _OUTLINE, "2025", "1")


class TestGetClient:
    def test_lazy_constructs_once(self, recap_ai_generate, monkeypatch):
        monkeypatch.setattr(recap_ai_generate, "_client", None)
        made = MagicMock()
        factory = MagicMock(return_value=made)
        monkeypatch.setattr(recap_ai_generate.boto3, "client", factory)
        first = recap_ai_generate._get_client()
        second = recap_ai_generate._get_client()
        assert first is made and second is made
        factory.assert_called_once()
        assert factory.call_args.args[0] == "bedrock-runtime"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("```json\n{}\n```", "{}"),
        ("```\n{}\n```", "{}"),
        ("```{}```", "{}"),
        ("{}", "{}"),
    ],
)
def test_strip_code_fences(recap_ai_generate, raw, expected):
    assert recap_ai_generate._strip_code_fences(raw) == expected
