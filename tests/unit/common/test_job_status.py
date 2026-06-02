"""Tests for the shared src/common/job_status.py module."""

from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

import common.job_status as job_status


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class _FakeHttpError(Exception):
    def __init__(self, status_code):
        super().__init__("http error")
        self.response = _FakeResponse(status_code)


class TestClassifyHttpError:
    @pytest.mark.parametrize("status_code", [401, 403])
    def test_auth_status_maps_to_espn_auth(self, status_code):
        assert (
            job_status.classify_http_error(_FakeHttpError(status_code)) == "ESPN_AUTH"
        )

    @pytest.mark.parametrize("status_code", [429, 500, 502, 503])
    def test_other_status_maps_to_upstream(self, status_code):
        assert job_status.classify_http_error(_FakeHttpError(status_code)) == "UPSTREAM"

    def test_no_response_maps_to_upstream(self):
        assert job_status.classify_http_error(Exception("boom")) == "UPSTREAM"


class TestWriteJobStatus:
    def test_noop_when_correlation_id_empty(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(job_status, "_dynamodb", mock_ddb):
            job_status.write_job_status("", "FAILED", "ONBOARD")
        mock_ddb.update_item.assert_not_called()

    def test_noop_when_table_env_missing(self, monkeypatch):
        monkeypatch.delenv("DYNAMODB_TABLE_NAME", raising=False)
        mock_ddb = MagicMock()
        with patch.object(job_status, "_dynamodb", mock_ddb):
            job_status.write_job_status("corr-1", "FAILED", "ONBOARD")
        mock_ddb.update_item.assert_not_called()

    def test_writes_key_status_and_ttl(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(job_status, "_dynamodb", mock_ddb):
            job_status.write_job_status("corr-1", "IN_PROGRESS", "REFRESH")
        kwargs = mock_ddb.update_item.call_args.kwargs
        assert kwargs["Key"] == {
            "PK": {"S": "JOB#corr-1"},
            "SK": {"S": "JOB_STATUS"},
        }
        values = kwargs["ExpressionAttributeValues"]
        assert values[":status"] == {"S": "IN_PROGRESS"}
        assert values[":request_type"] == {"S": "REFRESH"}
        assert int(values[":ttl"]["N"]) > 0
        assert "ttl = :ttl" in kwargs["UpdateExpression"]
        assert kwargs["ExpressionAttributeNames"]["#status"] == "status"

    def test_failure_code_stores_friendly_reason(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(job_status, "_dynamodb", mock_ddb):
            job_status.write_job_status(
                "corr-1", "FAILED", "ONBOARD", failure_code="ESPN_AUTH"
            )
        values = mock_ddb.update_item.call_args.kwargs["ExpressionAttributeValues"]
        assert values[":failure_code"] == {"S": "ESPN_AUTH"}
        assert values[":failure_reason"] == {
            "S": job_status.FAILURE_REASONS["ESPN_AUTH"]
        }

    def test_request_type_omitted_when_not_given(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(job_status, "_dynamodb", mock_ddb):
            job_status.write_job_status("corr-1", "COMPLETED")
        kwargs = mock_ddb.update_item.call_args.kwargs
        assert ":request_type" not in kwargs["ExpressionAttributeValues"]
        assert "request_type" not in kwargs["UpdateExpression"]

    def test_observability_attrs_included_when_present(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(job_status, "_dynamodb", mock_ddb):
            job_status.write_job_status(
                "corr-1",
                "IN_PROGRESS",
                "ONBOARD",
                league_id="123",
                platform="ESPN",
                canonical_league_id="canon-1",
            )
        values = mock_ddb.update_item.call_args.kwargs["ExpressionAttributeValues"]
        assert values[":league_id"] == {"S": "123"}
        assert values[":platform"] == {"S": "ESPN"}
        assert values[":canonical_league_id"] == {"S": "canon-1"}

    def test_swallows_client_error(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        mock_ddb.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "UpdateItem"
        )
        with patch.object(job_status, "_dynamodb", mock_ddb):
            # Best-effort: must not raise.
            job_status.write_job_status("corr-1", "FAILED", "ONBOARD")
