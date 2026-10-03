"""Tests for the shared src/common/league_members.py module."""

from unittest.mock import MagicMock

import botocore.exceptions
import pytest

from common import league_members


def _client_error(code: str) -> botocore.exceptions.ClientError:
    return botocore.exceptions.ClientError({"Error": {"Code": code}}, "PutItem")


class TestMemberItem:
    def test_builds_keys_and_index_attributes(self):
        item = league_members.member_item("canon-1", "user_1", "2026-01-01T00:00:00Z")
        assert item == {
            "PK": "LEAGUE#canon-1",
            "SK": "MEMBER#user_1",
            "member_user_id": "user_1",
            "joined_at": "2026-01-01T00:00:00Z",
        }

    def test_defaults_joined_at_to_now(self):
        item = league_members.member_item("canon-1", "user_1")
        assert item["joined_at"].endswith("+00:00")


class TestMemberTransactPut:
    def test_typed_unconditional_put(self):
        entry = league_members.member_transact_put(
            "tbl", "canon-1", "user_1", "2026-01-01T00:00:00Z"
        )
        assert entry == {
            "Put": {
                "TableName": "tbl",
                "Item": {
                    "PK": {"S": "LEAGUE#canon-1"},
                    "SK": {"S": "MEMBER#user_1"},
                    "member_user_id": {"S": "user_1"},
                    "joined_at": {"S": "2026-01-01T00:00:00Z"},
                },
            }
        }


class TestPutLeagueMember:
    def test_creates_new_item(self):
        table = MagicMock()
        assert league_members.put_league_member(
            table, "canon-1", "user_1", "2026-01-01T00:00:00Z"
        )
        table.put_item.assert_called_once_with(
            Item={
                "PK": "LEAGUE#canon-1",
                "SK": "MEMBER#user_1",
                "member_user_id": "user_1",
                "joined_at": "2026-01-01T00:00:00Z",
            },
            ConditionExpression="attribute_not_exists(PK)",
        )

    def test_already_indexed_returns_false(self):
        table = MagicMock()
        table.put_item.side_effect = _client_error("ConditionalCheckFailedException")
        assert league_members.put_league_member(table, "canon-1", "user_1") is False

    def test_other_errors_propagate(self):
        table = MagicMock()
        table.put_item.side_effect = _client_error("ProvisionedThroughputExceeded")
        with pytest.raises(botocore.exceptions.ClientError):
            league_members.put_league_member(table, "canon-1", "user_1")
