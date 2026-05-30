"""Tests for utility functions in main.py."""

import json
import logging
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


def test_json_formatter_keys():
    from main import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    output = json.loads(formatter.format(record))
    assert output["level"] == "INFO"
    assert output["message"] == "hello world"
    assert "timestamp" in output
    assert "function" in output


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


class TestUpdateSubscriptionStatus:
    def test_sets_status_on_metadata_item(self, mock_table):
        from main import SubscriptionStatus, update_subscription_status

        update_subscription_status("canonical-abc", SubscriptionStatus.PAST_DUE)
        mock_table.update_item.assert_called_once_with(
            Key={"PK": "LEAGUE#canonical-abc", "SK": "METADATA"},
            UpdateExpression="SET subscription_status = :s",
            ConditionExpression="attribute_exists(PK)",
            ExpressionAttributeValues={":s": "PAST_DUE"},
        )


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
    def test_publish_failure_noop_when_unconfigured(self, monkeypatch):
        import main

        # No SNS topic configured -> client is None -> publish is a no-op.
        monkeypatch.setattr(main, "_sns_client", None)
        main.publish_failure("something broke")  # should not raise

    def test_publish_failure_publishes_when_configured(self, mock_sns_client):
        from main import publish_failure

        publish_failure("something broke")
        mock_sns_client.publish.assert_called_once()
        kwargs = mock_sns_client.publish.call_args.kwargs
        assert kwargs["Subject"] == "LeagueQL API Failure"
        assert "something broke" in kwargs["Message"]

    def test_publish_failure_swallows_publish_errors(self, mock_sns_client):
        from main import publish_failure

        mock_sns_client.publish.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "Publish"
        )
        # Failure to publish must not propagate out of the helper.
        publish_failure("something broke")
