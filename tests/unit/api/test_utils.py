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


class TestDeletePrefixedItems:
    def test_deletes_items_in_batches(self, mock_table):
        from main import delete_prefixed_items

        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.return_value = {
            "Items": [
                {"PK": "LEAGUE#abc", "SK": "MATCHUPS#2024"},
                {"PK": "LEAGUE#abc", "SK": "MATCHUPS#2023"},
            ]
        }
        delete_prefixed_items("LEAGUE#abc", "MATCHUPS#")
        assert mock_writer.delete_item.call_count == 2

    def test_handles_pagination(self, mock_table):
        from main import delete_prefixed_items

        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.side_effect = [
            {
                "Items": [{"PK": "LEAGUE#abc", "SK": "MATCHUPS#2023"}],
                "LastEvaluatedKey": {"PK": "LEAGUE#abc", "SK": "MATCHUPS#2023"},
            },
            {"Items": [{"PK": "LEAGUE#abc", "SK": "MATCHUPS#2024"}]},
        ]
        delete_prefixed_items("LEAGUE#abc", "MATCHUPS#")
        assert mock_writer.delete_item.call_count == 2

    def test_raises_500_on_boto_error(self, mock_table):
        from main import delete_prefixed_items

        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            side_effect=botocore.exceptions.ClientError(
                {"Error": {"Code": "InternalError", "Message": "fail"}}, "BatchWrite"
            )
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        with pytest.raises(HTTPException) as exc_info:
            delete_prefixed_items("LEAGUE#abc", "MATCHUPS#")
        assert exc_info.value.status_code == 500
