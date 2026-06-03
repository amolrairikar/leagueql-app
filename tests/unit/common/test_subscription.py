"""Unit tests for common.subscription (BE-015 shared subscription writes)."""

import os
from unittest.mock import MagicMock, patch

import pytest

import common.subscription as cs


class _ConditionalCheckFailed(Exception):
    """Stand-in for boto3's dynamically generated ConditionalCheckFailedException."""


@pytest.fixture
def mock_ddb():
    client = MagicMock()
    # The module catches ``_dynamodb.exceptions.ConditionalCheckFailedException``,
    # so it must resolve to a real exception class for ``except`` to work.
    client.exceptions.ConditionalCheckFailedException = _ConditionalCheckFailed
    with (
        patch.object(cs, "_dynamodb", client),
        patch.dict(os.environ, {"DYNAMODB_TABLE_NAME": "test-table"}),
    ):
        yield client


class TestRecordActiveSubscription:
    def test_applies_and_returns_true(self, mock_ddb):
        assert (
            cs.record_active_subscription(
                "canonical-abc", "2026-07-01T00:00:00+00:00", "sub_1"
            )
            is True
        )
        _, kwargs = mock_ddb.update_item.call_args
        assert kwargs["Key"] == {
            "PK": {"S": "LEAGUE#canonical-abc"},
            "SK": {"S": "METADATA"},
        }
        assert "REMOVE pending_checkout" in kwargs["UpdateExpression"]
        assert "subscription_end_time < :t" in kwargs["ConditionExpression"]
        assert "stripe_subscription_id = :sid" in kwargs["ConditionExpression"]
        assert kwargs["ExpressionAttributeValues"][":sid"] == {"S": "sub_1"}
        assert ":tu" not in kwargs["ExpressionAttributeValues"]

    def test_mark_trial_used_sets_flag(self, mock_ddb):
        cs.record_active_subscription(
            "canonical-abc",
            "2026-07-01T00:00:00+00:00",
            "sub_1",
            mark_trial_used=True,
        )
        _, kwargs = mock_ddb.update_item.call_args
        assert "trial_used = :tu" in kwargs["UpdateExpression"]
        assert kwargs["ExpressionAttributeValues"][":tu"] == {"BOOL": True}

    def test_noop_when_non_advancing_same_subscription(self, mock_ddb):
        mock_ddb.update_item.side_effect = _ConditionalCheckFailed()
        mock_ddb.get_item.return_value = {
            "Item": {"stripe_subscription_id": {"S": "sub_1"}}
        }
        assert (
            cs.record_active_subscription(
                "canonical-abc", "2026-07-01T00:00:00+00:00", "sub_1"
            )
            is False
        )

    def test_noop_when_no_subscription_recorded(self, mock_ddb):
        mock_ddb.update_item.side_effect = _ConditionalCheckFailed()
        mock_ddb.get_item.return_value = {"Item": {}}
        assert (
            cs.record_active_subscription(
                "canonical-abc", "2026-07-01T00:00:00+00:00", "sub_1"
            )
            is False
        )

    def test_raises_duplicate_when_different_subscription_recorded(self, mock_ddb):
        mock_ddb.update_item.side_effect = _ConditionalCheckFailed()
        mock_ddb.get_item.return_value = {
            "Item": {"stripe_subscription_id": {"S": "sub_existing"}}
        }
        with pytest.raises(cs.DuplicateSubscription):
            cs.record_active_subscription(
                "canonical-abc", "2026-07-01T00:00:00+00:00", "sub_new"
            )

    def test_writes_durable_trial_marker_with_native_identity(self, mock_ddb):
        cs.record_active_subscription(
            "canonical-abc",
            "2026-07-01T00:00:00+00:00",
            "sub_1",
            mark_trial_used=True,
            platform="SLEEPER",
            native_league_id="123",
        )
        mock_ddb.put_item.assert_called_once()
        _, kwargs = mock_ddb.put_item.call_args
        assert kwargs["Item"]["PK"] == {"S": "LEAGUE#123#PLATFORM#SLEEPER"}
        assert kwargs["Item"]["SK"] == {"S": "TRIAL_USED"}
        assert kwargs["Item"]["platform"] == {"S": "SLEEPER"}
        assert kwargs["Item"]["league_id"] == {"S": "123"}
        assert "trial_used_at" in kwargs["Item"]
        assert kwargs["ConditionExpression"] == "attribute_not_exists(PK)"
        # Deliberately no canonical_league_id (so the BE-007 delete sweep misses it).
        assert "canonical_league_id" not in kwargs["Item"]

    def test_durable_trial_marker_skipped_without_native_identity(self, mock_ddb):
        cs.record_active_subscription(
            "canonical-abc",
            "2026-07-01T00:00:00+00:00",
            "sub_1",
            mark_trial_used=True,
        )
        mock_ddb.put_item.assert_not_called()

    def test_durable_trial_marker_idempotent(self, mock_ddb):
        # A redelivered trialing event re-puts the marker; the conditional write
        # fails and is swallowed (the first-grant record is preserved).
        mock_ddb.put_item.side_effect = _ConditionalCheckFailed()
        assert (
            cs.record_active_subscription(
                "canonical-abc",
                "2026-07-01T00:00:00+00:00",
                "sub_1",
                mark_trial_used=True,
                platform="SLEEPER",
                native_league_id="123",
            )
            is True
        )

    def test_no_durable_marker_on_duplicate_subscription(self, mock_ddb):
        mock_ddb.update_item.side_effect = _ConditionalCheckFailed()
        mock_ddb.get_item.return_value = {
            "Item": {"stripe_subscription_id": {"S": "sub_existing"}}
        }
        with pytest.raises(cs.DuplicateSubscription):
            cs.record_active_subscription(
                "canonical-abc",
                "2026-07-01T00:00:00+00:00",
                "sub_new",
                mark_trial_used=True,
                platform="SLEEPER",
                native_league_id="123",
            )
        mock_ddb.put_item.assert_not_called()


class TestExpireSubscription:
    def test_expires_and_returns_true(self, mock_ddb):
        assert cs.expire_subscription("canonical-abc", "sub_1") is True
        _, kwargs = mock_ddb.update_item.call_args
        assert kwargs["ExpressionAttributeValues"][":past"] == {"S": cs.EXPIRED_AT}
        assert kwargs["ExpressionAttributeValues"][":sid"] == {"S": "sub_1"}
        assert "stripe_subscription_id = :sid" in kwargs["ConditionExpression"]
        assert "REMOVE pending_checkout" in kwargs["UpdateExpression"]

    def test_noop_when_not_recorded_subscription(self, mock_ddb):
        mock_ddb.update_item.side_effect = _ConditionalCheckFailed()
        assert cs.expire_subscription("canonical-abc", "sub_other") is False
