"""Unit tests for the pending-recap enqueue helper (BE-021)."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

import common.recap_queue as recap_queue
from common import feature_flags


@pytest.fixture(autouse=True)
def _queue_env(monkeypatch):
    monkeypatch.setenv("RECAP_QUEUE_TABLE", "test-table")


@pytest.fixture(autouse=True)
def _billing_on():
    feature_flags._override_for_testing({"billing": True})
    yield
    feature_flags._override_for_testing({"billing": False})


@pytest.fixture
def table():
    tbl = MagicMock()
    with patch.object(recap_queue, "_dynamodb") as ddb:
        ddb.Table.return_value = tbl
        yield tbl


def _conditional_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
    )


class TestRecordPendingRecap:
    def test_writes_pending_marker(self, table):
        recap_queue.record_pending_recap(
            canonical_league_id="123",
            platform="sleeper",
            correlation_id="cid",
            native_league_id="nat",
        )
        item = table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "RECAP_QUEUE"
        assert item["SK"] == "PENDING#123"
        assert item["canonical_league_id"] == "123"
        assert item["status"] == "pending"
        assert item["platform"] == "sleeper"
        assert item["native_league_id"] == "nat"
        assert item["correlation_id"] == "cid"
        assert "enqueued_at" in item
        # Conditional put must not clobber an in-flight marker.
        cond = table.put_item.call_args.kwargs["ConditionExpression"]
        assert "in_flight" in str(
            table.put_item.call_args.kwargs["ExpressionAttributeValues"].values()
        )
        assert "attribute_not_exists" in cond

    def test_omits_optional_fields_when_absent(self, table):
        recap_queue.record_pending_recap(canonical_league_id="123")
        item = table.put_item.call_args.kwargs["Item"]
        assert "platform" not in item
        assert "native_league_id" not in item

    def test_noop_when_table_unset(self, table, monkeypatch):
        monkeypatch.delenv("RECAP_QUEUE_TABLE", raising=False)
        recap_queue.record_pending_recap(canonical_league_id="123")
        table.put_item.assert_not_called()

    def test_noop_when_billing_disabled(self, table):
        feature_flags._override_for_testing({"billing": False})
        recap_queue.record_pending_recap(canonical_league_id="123")
        table.put_item.assert_not_called()

    def test_noop_when_recap_flag_disabled(self, table):
        # Billing stays ON but the recap kill-switch is OFF ⇒ no enqueue (BE-017).
        feature_flags._override_for_testing({"billing": True, "recap": False})
        recap_queue.record_pending_recap(canonical_league_id="123")
        table.put_item.assert_not_called()

    def test_inflight_conflict_is_swallowed(self, table):
        table.put_item.side_effect = _conditional_error()
        # Must not raise.
        recap_queue.record_pending_recap(canonical_league_id="123")

    def test_other_client_error_is_swallowed(self, table):
        table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}}, "PutItem"
        )
        recap_queue.record_pending_recap(canonical_league_id="123")

    def test_unexpected_error_is_swallowed(self, table):
        table.put_item.side_effect = RuntimeError("boom")
        recap_queue.record_pending_recap(canonical_league_id="123")
