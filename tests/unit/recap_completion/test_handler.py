"""Unit tests for the recap-completion Lambda (BE-022)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

_JOB = "arn:aws:bedrock:us-east-1:1:model-invocation-job/abc"


def _manifest() -> dict:
    return {
        "PK": f"RECAP_JOB#{_JOB}",
        "SK": "MANIFEST",
        "output_uri": "s3://test-bucket/output/job/",
        "model": "us.meta.llama3-3-70b-instruct-v1:0",
        "league_ids": ["123"],
        "records": {
            "rec1": {"canonical_league_id": "123", "season": "2024", "week": "01"},
        },
    }


def _event(status: str, job=_JOB) -> dict:
    detail = {"status": status}
    if job is not None:
        detail["batchJobArn"] = job
    return {"detail": detail}


def _output_line(record_id="rec1", generation="Headline\n\nBody.") -> str:
    return json.dumps(
        {"recordId": record_id, "modelOutput": {"generation": generation}}
    )


def make_table(manifest: dict | None) -> MagicMock:
    table = MagicMock()
    table.get_item.return_value = {"Item": manifest} if manifest else {}
    return table


def make_s3(lines: list[str]) -> MagicMock:
    s3 = MagicMock()
    s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "output/job/x.jsonl.out"}],
        "IsTruncated": False,
    }
    body = MagicMock()
    body.read.return_value = ("\n".join(lines)).encode("utf-8")
    s3.get_object.return_value = {"Body": body}
    return s3


def _conditional_error(op="PutItem") -> ClientError:
    return ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, op)


@pytest.fixture
def patched(completion):
    table = make_table(_manifest())
    s3 = make_s3([_output_line()])
    with (
        patch.object(completion, "_table", table),
        patch.object(completion, "_s3", s3),
        patch.object(completion, "publish_failure") as alert,
    ):
        yield completion, table, s3, alert


class TestCompleted:
    def test_writes_recap_and_clears_marker_and_manifest(self, patched):
        completion, table, s3, _ = patched
        result = completion._handle(_event("Completed"))

        assert result == {"status": "completed", "job_state": "Completed", "written": 1}
        # Recap written with conditional (idempotent) put.
        recap_put = next(
            c
            for c in table.put_item.call_args_list
            if c.kwargs["Item"]["SK"].startswith("MATCHUP_RECAP#")
        )
        item = recap_put.kwargs["Item"]
        assert item["PK"] == "LEAGUE#123"
        assert item["SK"] == "MATCHUP_RECAP#2024#WEEK#01"
        assert item["data"][0]["headline"] == "Headline"
        assert item["data"][0]["model"] == "us.meta.llama3-3-70b-instruct-v1:0"
        assert recap_put.kwargs["ConditionExpression"] == "attribute_not_exists(SK)"
        # Marker deleted conditionally on the job, manifest deleted.
        marker_delete = next(
            c
            for c in table.delete_item.call_args_list
            if c.kwargs["Key"]["SK"] == "PENDING#123"
        )
        assert marker_delete.kwargs["ExpressionAttributeValues"][":job"] == _JOB
        assert any(
            c.kwargs["Key"]["PK"] == f"RECAP_JOB#{_JOB}"
            for c in table.delete_item.call_args_list
        )

    def test_already_written_is_idempotent(self, patched):
        completion, table, s3, _ = patched
        table.put_item.side_effect = _conditional_error()
        result = completion._handle(_event("Completed"))
        assert result["written"] == 0  # nothing new, no raise

    def test_record_not_in_manifest_skipped(self, completion):
        table = make_table(_manifest())
        s3 = make_s3([_output_line(record_id="unknown")])
        with (
            patch.object(completion, "_table", table),
            patch.object(completion, "_s3", s3),
        ):
            result = completion._handle(_event("Completed"))
        assert result["written"] == 0

    def test_record_with_error_skipped(self, completion):
        table = make_table(_manifest())
        bad = json.dumps({"recordId": "rec1", "error": "model failure"})
        s3 = make_s3([bad])
        with (
            patch.object(completion, "_table", table),
            patch.object(completion, "_s3", s3),
        ):
            result = completion._handle(_event("Completed"))
        assert result["written"] == 0

    def test_empty_generation_skipped(self, completion):
        table = make_table(_manifest())
        s3 = make_s3([_output_line(generation="")])
        with (
            patch.object(completion, "_table", table),
            patch.object(completion, "_s3", s3),
        ):
            result = completion._handle(_event("Completed"))
        assert result["written"] == 0

    def test_unparsable_line_skipped(self, completion):
        table = make_table(_manifest())
        s3 = make_s3(["not json", "", _output_line()])
        with (
            patch.object(completion, "_table", table),
            patch.object(completion, "_s3", s3),
        ):
            result = completion._handle(_event("Completed"))
        assert result["written"] == 1


class TestPartiallyCompleted:
    def test_resets_markers(self, patched):
        completion, table, s3, _ = patched
        result = completion._handle(_event("PartiallyCompleted"))
        assert result["job_state"] == "PartiallyCompleted"
        # Marker reset to pending (update, not delete).
        update = table.update_item.call_args
        assert update.kwargs["ExpressionAttributeValues"][":pending"] == "pending"
        assert update.kwargs["ExpressionAttributeValues"][":job"] == _JOB


class TestFailure:
    @pytest.mark.parametrize("status", ["Failed", "Stopped", "Expired"])
    def test_resets_markers_and_alerts(self, patched, status):
        completion, table, s3, alert = patched
        result = completion._handle(_event(status))
        assert result["status"] == "failed"
        alert.assert_called_once()
        table.update_item.assert_called_once()  # reset marker
        s3.get_object.assert_not_called()  # no outputs read on failure


class TestIgnored:
    def test_missing_job_arn(self, completion):
        result = completion._handle(_event("Completed", job=None))
        assert result == {"status": "ignored", "reason": "malformed_event"}

    def test_non_terminal_status(self, completion):
        result = completion._handle(_event("InProgress"))
        assert result["reason"] == "non_terminal:InProgress"

    def test_no_manifest(self, completion):
        table = make_table(None)
        with patch.object(completion, "_table", table):
            result = completion._handle(_event("Completed"))
        assert result == {"status": "ignored", "reason": "no_manifest"}

    def test_non_dict_event(self, completion):
        result = completion._handle("garbage")
        assert result["reason"] == "malformed_event"


class TestMarkerConflict:
    def test_marker_repointed_under_newer_job_is_left(self, patched):
        completion, table, s3, _ = patched
        table.delete_item.side_effect = [_conditional_error("DeleteItem"), None]
        # Must not raise; the conditional delete failure is swallowed.
        result = completion._handle(_event("Completed"))
        assert result["status"] == "completed"
