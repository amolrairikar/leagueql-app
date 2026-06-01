"""Tests for the shared src/common/sns.py module."""

from unittest.mock import MagicMock, patch

import common.sns as sns


def test_publish_failure_noop_when_unconfigured():
    # No SNS topic configured -> client is None -> publish is a no-op.
    with patch.object(sns, "_sns_client", None):
        sns.publish_failure("something broke", subject="X")  # should not raise


def test_publish_failure_publishes_when_configured():
    mock_client = MagicMock()
    with (
        patch.object(sns, "_sns_client", mock_client),
        patch.object(sns, "_sns_topic_arn", "arn:aws:sns:us-east-1:123:test-topic"),
    ):
        sns.publish_failure("something broke", subject="LeagueQL Test Failure")

    mock_client.publish.assert_called_once()
    kwargs = mock_client.publish.call_args.kwargs
    assert kwargs["Subject"] == "LeagueQL Test Failure"
    assert kwargs["TopicArn"] == "arn:aws:sns:us-east-1:123:test-topic"
    assert "something broke" in kwargs["Message"]
    assert "Correlation ID" in kwargs["Message"]


def test_publish_failure_swallows_publish_errors():
    mock_client = MagicMock()
    mock_client.publish.side_effect = Exception("boom")
    # Failure to publish must not propagate out of the helper.
    with patch.object(sns, "_sns_client", mock_client):
        sns.publish_failure("something broke", subject="X")
