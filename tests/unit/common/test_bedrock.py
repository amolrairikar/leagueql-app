"""Unit tests for the Bedrock batch recap helper (BE-022)."""

import json
from unittest.mock import MagicMock, patch

import pytest

import common.bedrock as bedrock


@pytest.fixture(autouse=True)
def _model_env(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "us.meta.llama3-3-70b-instruct-v1:0")


class TestBuildRecapRecord:
    def test_builds_batch_record_with_modelinput(self):
        highlights = {"season": "2024", "week": 1, "matchups": []}
        record = bedrock.build_recap_record("rec00000001", highlights)

        assert record["recordId"] == "rec00000001"
        model_input = record["modelInput"]
        assert model_input["max_gen_len"] == bedrock._MAX_GEN_LEN
        assert model_input["temperature"] == bedrock._TEMPERATURE
        # The highlights JSON and the system prompt are both embedded in the prompt.
        assert json.dumps(highlights) in model_input["prompt"]
        assert "fantasy football columnist" in model_input["prompt"]

    def test_prompt_uses_llama_chat_template(self):
        record = bedrock.build_recap_record("rec00000001", {})
        prompt = record["modelInput"]["prompt"]
        assert prompt.startswith("<|begin_of_text|>")
        assert "<|start_header_id|>system<|end_header_id|>" in prompt
        assert "<|start_header_id|>user<|end_header_id|>" in prompt
        assert prompt.endswith("<|start_header_id|>assistant<|end_header_id|>\n\n")

    def test_system_prompt_includes_fact_fidelity_guardrail(self):
        assert "chris_j" in bedrock._SYSTEM_PROMPT
        assert "Never invent" in bedrock._SYSTEM_PROMPT


class TestSubmitBatchJob:
    def test_submits_job_and_returns_arn(self):
        client = MagicMock()
        client.create_model_invocation_job.return_value = {"jobArn": "arn:job:1"}
        with patch.object(bedrock, "_bedrock_client", client):
            arn = bedrock.submit_batch_job(
                job_name="leagueql-recap-1",
                input_uri="s3://b/input/leagueql-recap-1.jsonl",
                output_uri="s3://b/output/leagueql-recap-1/",
                role_arn="arn:role:batch",
            )

        assert arn == "arn:job:1"
        kwargs = client.create_model_invocation_job.call_args.kwargs
        assert kwargs["jobName"] == "leagueql-recap-1"
        assert kwargs["roleArn"] == "arn:role:batch"
        assert kwargs["modelId"] == "us.meta.llama3-3-70b-instruct-v1:0"
        assert (
            kwargs["inputDataConfig"]["s3InputDataConfig"]["s3Uri"]
            == "s3://b/input/leagueql-recap-1.jsonl"
        )
        assert (
            kwargs["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"]
            == "s3://b/output/leagueql-recap-1/"
        )


class TestParseRecapOutput:
    def test_parses_generation_into_headline_and_body(self):
        out = {"generation": "The Headline\n\nFirst para.\n\n\n\nSecond para.\n"}
        assert bedrock.parse_recap_output(out) == {
            "headline": "The Headline",
            "body": "First para.\n\nSecond para.",
        }

    def test_leading_blank_lines_before_headline(self):
        out = {"generation": "\n\n  Title  \n\nBody."}
        assert bedrock.parse_recap_output(out) == {
            "headline": "Title",
            "body": "Body.",
        }

    def test_missing_generation_returns_empty(self):
        assert bedrock.parse_recap_output({}) == {"headline": "", "body": ""}

    def test_only_headline(self):
        assert bedrock.parse_recap_output({"generation": "Just a headline"}) == {
            "headline": "Just a headline",
            "body": "",
        }

    def test_parse_recap_empty(self):
        assert bedrock._parse_recap("") == {"headline": "", "body": ""}
