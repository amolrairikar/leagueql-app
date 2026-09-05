"""Tests for the nightly admin-report Lambda handler (src/admin_report/handler.py)."""

from unittest.mock import patch

import pytest
import requests


def _posted_embed(mock_post) -> dict:
    """Return the single embed captured from the mocked webhook POST."""
    return mock_post.call_args.kwargs["json"]["embeds"][0]


def _fields(embed: dict) -> dict[str, str]:
    """Map an embed's field names to their values for easy assertions."""
    return {field["name"]: field["value"] for field in embed["fields"]}


class TestDigest:
    def test_posts_expected_metrics(self, handler, mock_table, mock_post):
        from datetime import timedelta

        now = handler.datetime.now(handler.timezone.utc)
        recent = now.isoformat()
        old = (now - timedelta(days=10)).isoformat()  # counted in total, not in 24h
        mock_table.query.return_value = {
            "Items": [
                {
                    "platform": "ESPN",
                    "onboarded_at": recent,
                    "last_accessed_at": recent,
                },
                {
                    "platform": "ESPN",
                    "active_platform": "SLEEPER",
                    "onboarded_at": recent,
                    "last_accessed_at": recent,
                },
                {"platform": "SLEEPER", "onboarded_at": old},  # never accessed
            ]
        }

        handler.lambda_handler({}, None)

        embed = _posted_embed(mock_post)
        assert embed["color"] == handler._COLOR_GREEN
        fields = _fields(embed)
        assert fields["Total onboarded"] == "3"
        assert fields[f"Active ({handler.ACTIVE_DAYS}d)"] == "2"
        assert fields["ESPN / SLEEPER"] == "1 / 2"
        assert "Last 24h: **2**" in fields["New onboards"]

    def test_empty_table_posts_zeroes(self, handler, mock_table, mock_post):
        mock_table.query.return_value = {"Items": []}

        handler.lambda_handler({}, None)

        fields = _fields(_posted_embed(mock_post))
        assert fields["Total onboarded"] == "0"
        assert fields["ESPN / SLEEPER"] == "0 / 0"

    def test_paginates_all_pages(self, handler, mock_table, mock_post):
        now = handler.datetime.now(handler.timezone.utc).isoformat()
        mock_table.query.side_effect = [
            {
                "Items": [{"platform": "ESPN", "onboarded_at": now}],
                "LastEvaluatedKey": {"SK": "METADATA", "onboarded_at": now},
            },
            {"Items": [{"platform": "SLEEPER", "onboarded_at": now}]},
        ]

        handler.lambda_handler({}, None)

        assert mock_table.query.call_count == 2
        # The second query must carry the ExclusiveStartKey from the first page.
        assert "ExclusiveStartKey" in mock_table.query.call_args_list[1].kwargs
        fields = _fields(_posted_embed(mock_post))
        assert fields["Total onboarded"] == "2"


class TestFailureModes:
    def test_unset_webhook_raises(self, handler, mock_table, mock_post):
        with (
            patch.object(handler, "_WEBHOOK_URL", ""),
            pytest.raises(RuntimeError, match="webhook URL is not configured"),
        ):
            handler.lambda_handler({}, None)
        mock_post.assert_not_called()
        mock_table.query.assert_not_called()

    def test_query_failure_reraises_without_posting(
        self, handler, mock_table, mock_post
    ):
        mock_table.query.side_effect = RuntimeError("dynamodb down")
        with pytest.raises(RuntimeError, match="dynamodb down"):
            handler.lambda_handler({}, None)
        mock_post.assert_not_called()

    def test_non_2xx_response_reraises(self, handler, mock_table, mock_post):
        mock_table.query.return_value = {"Items": []}
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError("500")
        with pytest.raises(requests.HTTPError):
            handler.lambda_handler({}, None)
