"""Tests for utility functions in main.py.

JSON logging (``JsonFormatter`` / ``setup_logger``) is shared code now exercised by
``tests/unit/common/test_logging_utils.py``.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import botocore.exceptions
import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def import_main():
    import main  # noqa: F401


def test_convert_decimals_flat_dict():
    from main import convert_decimals

    result = convert_decimals({"score": Decimal("105.75"), "week": 1})
    assert result == {"score": 105.75, "week": 1}


def test_convert_decimals_nested():
    from main import convert_decimals

    result = convert_decimals({"outer": {"inner": Decimal("3.14")}})
    assert result == {"outer": {"inner": 3.14}}


def test_convert_decimals_list():
    from main import convert_decimals

    result = convert_decimals([Decimal("1.1"), Decimal("2.2"), 3])
    assert result == [1.1, 2.2, 3]


def test_convert_decimals_passthrough():
    from main import convert_decimals

    assert convert_decimals("hello") == "hello"
    assert convert_decimals(42) == 42
    assert convert_decimals(None) is None


class TestLookupLeague:
    def test_returns_canonical_id(self, mock_table, league_lookup_item):
        from main import Platform, lookup_league

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        result = lookup_league("123", Platform.SLEEPER)
        assert result == "canonical-abc"

    def test_raises_404_when_not_found(self, mock_table):
        from main import Platform, lookup_league

        mock_table.get_item.return_value = {}
        with pytest.raises(HTTPException) as exc_info:
            lookup_league("999", Platform.SLEEPER)
        assert exc_info.value.status_code == 404

    def test_raises_500_when_canonical_id_missing(self, mock_table):
        from main import Platform, lookup_league

        mock_table.get_item.return_value = {
            "Item": {"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}
        }
        with pytest.raises(HTTPException) as exc_info:
            lookup_league("123", Platform.SLEEPER)
        assert exc_info.value.status_code == 500

    def test_raises_500_on_boto_error(self, mock_table):
        from main import Platform, lookup_league

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
        )
        with pytest.raises(HTTPException) as exc_info:
            lookup_league("123", Platform.SLEEPER)
        assert exc_info.value.status_code == 500


class TestGetLeagueMetadata:
    def test_returns_item(self, mock_table, league_metadata_item):
        from main import get_league_metadata

        mock_table.get_item.return_value = {"Item": league_metadata_item}
        result = get_league_metadata("canonical-abc")
        assert result["league_name"] == "Test League"

    def test_raises_500_when_not_found(self, mock_table):
        from main import get_league_metadata

        mock_table.get_item.return_value = {}
        with pytest.raises(HTTPException) as exc_info:
            get_league_metadata("canonical-abc")
        assert exc_info.value.status_code == 500

    def test_raises_500_on_boto_error(self, mock_table):
        from main import get_league_metadata

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
        )
        with pytest.raises(HTTPException) as exc_info:
            get_league_metadata("canonical-abc")
        assert exc_info.value.status_code == 500


class TestGetLeagueSeasons:
    def test_returns_sorted_seasons(self, mock_table):
        from main import get_league_seasons

        mock_table.query.return_value = {
            "Items": [
                {"seasons": {"2024", "2022"}},
                {"seasons": {"2023"}},
            ]
        }
        result = get_league_seasons("canonical-abc")
        assert result == ["2022", "2023", "2024"]

    def test_merges_seasons_across_items(self, mock_table):
        from main import get_league_seasons

        mock_table.query.return_value = {
            "Items": [
                {"seasons": {"2021"}},
                {"seasons": {"2021", "2022"}},
            ]
        }
        result = get_league_seasons("canonical-abc")
        assert result == ["2021", "2022"]

    def test_raises_500_when_no_items(self, mock_table):
        from main import get_league_seasons

        mock_table.query.return_value = {"Items": []}
        with pytest.raises(HTTPException) as exc_info:
            get_league_seasons("canonical-abc")
        assert exc_info.value.status_code == 500

    def test_raises_500_on_boto_error(self, mock_table):
        from main import get_league_seasons

        mock_table.query.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "Query"
        )
        with pytest.raises(HTTPException) as exc_info:
            get_league_seasons("canonical-abc")
        assert exc_info.value.status_code == 500


class TestUpdateLeagueCount:
    def test_increments_count(self, mock_table):
        from main import update_league_count

        update_league_count(1)
        mock_table.update_item.assert_called_once_with(
            Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
            UpdateExpression="ADD league_count :delta",
            ExpressionAttributeValues={":delta": Decimal("1")},
        )

    def test_decrements_count(self, mock_table):
        from main import update_league_count

        update_league_count(-1)
        mock_table.update_item.assert_called_once_with(
            Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
            UpdateExpression="ADD league_count :delta",
            ExpressionAttributeValues={":delta": Decimal("-1")},
        )


class TestUpdateSubscriptionEndTime:
    def test_sets_end_time_on_metadata_item(self, mock_table):
        from main import update_subscription_end_time

        update_subscription_end_time("canonical-abc", "2026-07-01T00:00:00+00:00")
        mock_table.update_item.assert_called_once_with(
            Key={"PK": "LEAGUE#canonical-abc", "SK": "METADATA"},
            UpdateExpression="SET subscription_end_time = :s",
            ConditionExpression="attribute_exists(PK)",
            ExpressionAttributeValues={":s": "2026-07-01T00:00:00+00:00"},
        )


class TestRequireActiveSubscription:
    def _meta(self, end_time):
        item = {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}
        if end_time is not None:
            item["subscription_end_time"] = end_time
        return item

    def test_future_end_time_passes(self, mock_table):
        from main import require_active_subscription

        mock_table.get_item.return_value = {
            "Item": self._meta("2999-01-01T00:00:00+00:00")
        }
        # Should not raise.
        require_active_subscription("canonical-abc")

    def test_past_end_time_raises_402(self, mock_table):
        from fastapi import HTTPException

        from main import require_active_subscription

        mock_table.get_item.return_value = {
            "Item": self._meta("2000-01-01T00:00:00+00:00")
        }
        with pytest.raises(HTTPException) as exc:
            require_active_subscription("canonical-abc")
        assert exc.value.status_code == 402

    def test_absent_end_time_raises_402(self, mock_table):
        from fastapi import HTTPException

        from main import require_active_subscription

        mock_table.get_item.return_value = {"Item": self._meta(None)}
        with pytest.raises(HTTPException) as exc:
            require_active_subscription("canonical-abc")
        assert exc.value.status_code == 402

    def test_unparseable_end_time_raises_402(self, mock_table):
        from fastapi import HTTPException

        from main import require_active_subscription

        mock_table.get_item.return_value = {"Item": self._meta("not-a-date")}
        with pytest.raises(HTTPException) as exc:
            require_active_subscription("canonical-abc")
        assert exc.value.status_code == 402

    def test_uses_provided_metadata_without_fetching(self, mock_table):
        from main import require_active_subscription

        # Pre-fetched metadata short-circuits the DynamoDB read.
        require_active_subscription(
            "canonical-abc", metadata=self._meta("2999-01-01T00:00:00+00:00")
        )
        mock_table.get_item.assert_not_called()


class TestDeleteLeagueHelpers:
    def _setup_writer(self, mock_table):
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        return mock_writer

    def test_query_all_keys_paginates(self, mock_table):
        from main import _query_all_keys

        mock_table.query.side_effect = [
            {
                "Items": [{"PK": "LEAGUE#abc", "SK": "TEAMS#2024"}],
                "LastEvaluatedKey": {"PK": "x", "SK": "y"},
            },
            {"Items": [{"PK": "LEAGUE#abc", "SK": "TEAMS#2025"}]},
        ]
        keys = _query_all_keys({"KeyConditionExpression": "ignored"})
        assert keys == [
            {"PK": "LEAGUE#abc", "SK": "TEAMS#2024"},
            {"PK": "LEAGUE#abc", "SK": "TEAMS#2025"},
        ]
        assert mock_table.query.call_count == 2

    def test_collect_league_keys_merges_pk_and_gsi(self, mock_table):
        from main import collect_league_keys

        mock_table.query.side_effect = [
            # canonical PK items (METADATA, views, orphan-prone migration item)
            {
                "Items": [
                    {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"},
                    {
                        "PK": "LEAGUE#canonical-abc",
                        "SK": "PLATFORM_MIGRATION#SLEEPER#ESPN",
                    },
                ]
            },
            # GSI1 LEAGUE_LOOKUP items on their own PK
            {"Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}]},
        ]
        keys = collect_league_keys("canonical-abc")
        assert {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"} in keys
        assert {
            "PK": "LEAGUE#canonical-abc",
            "SK": "PLATFORM_MIGRATION#SLEEPER#ESPN",
        } in keys
        assert {"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"} in keys

    def test_delete_all_league_items_deletes_everything(
        self, mock_table, mock_time_sleep
    ):
        from main import delete_all_league_items

        writer = self._setup_writer(mock_table)
        mock_table.query.side_effect = [
            {"Items": [{"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}]},
            {"Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}]},
            {"Items": []},
            {"Items": []},
        ]
        delete_all_league_items("canonical-abc")
        writer.delete_item.assert_any_call(
            Key={"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}
        )
        writer.delete_item.assert_any_call(
            Key={"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}
        )

    def test_delete_all_league_items_noop_when_empty(self, mock_table, mock_time_sleep):
        from main import delete_all_league_items

        writer = self._setup_writer(mock_table)
        mock_table.query.return_value = {"Items": []}
        delete_all_league_items("canonical-abc")
        writer.delete_item.assert_not_called()
        mock_time_sleep.assert_not_called()

    def test_delete_all_league_items_retries_until_clean(
        self, mock_table, mock_time_sleep
    ):
        from main import delete_all_league_items

        writer = self._setup_writer(mock_table)
        mock_table.query.side_effect = [
            # pass 1: an item on the canonical PK, GSI1 empty
            {"Items": [{"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}]},
            {"Items": []},
            # pass 2: GSI1 was lagging, a lookup item now surfaces
            {"Items": []},
            {"Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}]},
            # pass 3: clean
            {"Items": []},
            {"Items": []},
        ]
        delete_all_league_items("canonical-abc")
        assert writer.delete_item.call_count == 2

    def test_delete_all_league_items_exits_clean_after_final_pass(
        self, mock_table, mock_time_sleep
    ):
        # With a single attempt that deletes items, the loop runs to completion and
        # the post-loop verification finds nothing remaining -> clean exit (no raise).
        from main import delete_all_league_items

        writer = self._setup_writer(mock_table)
        mock_table.query.side_effect = [
            # attempt 1 collect: one item on the PK, GSI empty
            {"Items": [{"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}]},
            {"Items": []},
            # post-loop verification: clean
            {"Items": []},
            {"Items": []},
        ]
        delete_all_league_items("canonical-abc", max_attempts=1)
        writer.delete_item.assert_called_once()

    def test_delete_all_league_items_raises_when_orphans_remain(
        self, mock_table, mock_time_sleep, mock_sns_client
    ):
        from main import delete_all_league_items

        self._setup_writer(mock_table)
        # Every collect pass keeps returning the same item: it never clears.
        mock_table.query.return_value = {
            "Items": [{"PK": "LEAGUE#canonical-abc", "SK": "TEAMS#2024"}]
        }
        with pytest.raises(HTTPException) as exc_info:
            delete_all_league_items("canonical-abc", max_attempts=2)
        assert exc_info.value.status_code == 500
        assert "fully delete" in exc_info.value.detail.lower()
        # Orphaned items should trigger an SNS failure notification.
        mock_sns_client.publish.assert_called_once()
        kwargs = mock_sns_client.publish.call_args.kwargs
        assert "canonical-abc" in kwargs["Message"]
        assert "TEAMS#2024" in kwargs["Message"]

    def test_delete_all_league_items_raises_on_query_error(self, mock_table):
        from main import delete_all_league_items

        mock_table.query.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "Query"
        )
        with pytest.raises(botocore.exceptions.ClientError):
            delete_all_league_items("canonical-abc")


class TestPublishFailure:
    # The shared publish/no-op/error-swallow behavior is covered by
    # tests/unit/common/test_sns.py; here we verify the API binds its own subject.
    def test_publish_failure_binds_api_subject(self, mock_sns_client):
        from main import publish_failure

        publish_failure("something broke")
        mock_sns_client.publish.assert_called_once()
        kwargs = mock_sns_client.publish.call_args.kwargs
        assert kwargs["Subject"] == "LeagueQL API Failure"
        assert "something broke" in kwargs["Message"]


class TestJobStatusHelpers:
    def test_create_job_status_omits_optional_fields(self, mock_table):
        # With no league_id/platform, the IN_PROGRESS item carries only the
        # canonical id, exercising the optional-field skip branches.
        from main import create_job_status

        create_job_status(
            correlation_id="corr-1",
            request_type="ONBOARD",
            canonical_league_id="canonical-abc",
        )
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "JOB#corr-1"
        assert item["status"] == "IN_PROGRESS"
        assert "league_id" not in item
        assert "platform" not in item
        assert item["canonical_league_id"] == "canonical-abc"

    def test_create_job_status_includes_optional_fields(self, mock_table):
        from main import create_job_status

        create_job_status(
            correlation_id="corr-1",
            request_type="REFRESH",
            league_id="123",
            platform="SLEEPER",
        )
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["league_id"] == "123"
        assert item["platform"] == "SLEEPER"

    def test_create_job_status_swallows_client_error(self, mock_table):
        # A failure to write JOB_STATUS must not propagate (best-effort).
        from main import create_job_status

        mock_table.put_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "PutItem"
        )
        create_job_status(correlation_id="corr-1", request_type="ONBOARD")

    def test_get_job_status_returns_item(self, mock_table):
        from main import get_job_status

        mock_table.get_item.return_value = {"Item": {"status": "COMPLETED"}}
        assert get_job_status("corr-1") == {"status": "COMPLETED"}

    def test_get_job_status_returns_none_when_absent(self, mock_table):
        from main import get_job_status

        mock_table.get_item.return_value = {}
        assert get_job_status("corr-1") is None

    def test_get_job_status_raises_500_on_client_error(self, mock_table):
        from fastapi import HTTPException

        from main import get_job_status

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
        )
        with pytest.raises(HTTPException) as exc_info:
            get_job_status("corr-1")
        assert exc_info.value.status_code == 500

    def test_set_active_job_updates_metadata(self, mock_table):
        from main import set_active_job

        set_active_job("canonical-abc", "corr-1")
        kwargs = mock_table.update_item.call_args.kwargs
        assert kwargs["ExpressionAttributeValues"] == {":j": "corr-1"}

    def test_set_active_job_swallows_client_error(self, mock_table):
        # Setting the active-job pointer is best-effort; errors are logged only.
        from main import set_active_job

        mock_table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "UpdateItem"
        )
        set_active_job("canonical-abc", "corr-1")
