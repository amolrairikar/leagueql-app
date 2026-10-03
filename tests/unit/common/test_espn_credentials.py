"""Tests for the shared ESPN credential engine (src/common/espn_credentials.py)."""

import time
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from common import espn_credentials
from common.espn_credentials import EspnCredentialClient, ESPNReauthRequired


def _client(**overrides):
    """Build an EspnCredentialClient with MagicMock deps, overridable per test."""
    deps = {
        "table": MagicMock(),
        "kms_client": MagicMock(),
        "kms_key_id": "key-123",
    }
    deps.update(overrides)
    return EspnCredentialClient(**deps)


class TestEncryptDecrypt:
    def test_roundtrip(self):
        kms = MagicMock()
        kms.encrypt.return_value = {"CiphertextBlob": b"cipher"}
        kms.decrypt.return_value = {"Plaintext": b"cookie-value"}
        client = _client(kms_client=kms)

        ciphertext = client.encrypt("cookie-value")
        assert isinstance(ciphertext, str)
        kms.encrypt.assert_called_once_with(KeyId="key-123", Plaintext=b"cookie-value")

        assert client.decrypt(ciphertext) == "cookie-value"


class TestStoreCredentials:
    def test_encrypts_and_persists(self):
        table = MagicMock()
        kms = MagicMock()
        kms.encrypt.side_effect = [
            {"CiphertextBlob": b"enc-swid"},
            {"CiphertextBlob": b"enc-s2"},
        ]
        client = _client(table=table, kms_client=kms)

        client.store_credentials("user_1", "{SWID}", "s2-cookie")

        item = table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "USER#user_1"
        assert item["SK"] == "ESPN_CREDENTIALS"
        # Stored cookie fields are ciphertext, never the plaintext cookies.
        assert item["swid"] != "{SWID}"
        assert item["espn_s2"] != "s2-cookie"
        assert item["updated_at"] <= int(time.time())


class TestGetCredentials:
    def test_returns_decrypted_pair(self):
        table = MagicMock()
        table.get_item.return_value = {
            "Item": {"swid": "c3dpZA==", "espn_s2": "czI="}  # base64 placeholders
        }
        kms = MagicMock()
        kms.decrypt.side_effect = [
            {"Plaintext": b"{SWID}"},
            {"Plaintext": b"s2-cookie"},
        ]
        client = _client(table=table, kms_client=kms)

        assert client.get_credentials("user_1") == ("{SWID}", "s2-cookie")

    def test_missing_item_raises_reauth(self):
        table = MagicMock()
        table.get_item.return_value = {}
        with pytest.raises(ESPNReauthRequired):
            _client(table=table).get_credentials("user_1")


class TestGetStoredCredentials:
    def test_returns_cookies_and_version(self):
        table = MagicMock()
        table.get_item.return_value = {
            "Item": {"swid": "c3dpZA==", "espn_s2": "czI=", "updated_at": 1700}
        }
        kms = MagicMock()
        kms.decrypt.side_effect = [
            {"Plaintext": b"{SWID}"},
            {"Plaintext": b"s2-cookie"},
        ]
        client = _client(table=table, kms_client=kms)

        assert client.get_stored_credentials("user_1") == ("{SWID}", "s2-cookie", 1700)

    def test_missing_updated_at_returns_none_version(self):
        table = MagicMock()
        table.get_item.return_value = {"Item": {"swid": "c3dpZA==", "espn_s2": "czI="}}
        kms = MagicMock()
        kms.decrypt.return_value = {"Plaintext": b"x"}
        assert _client(table=table, kms_client=kms).get_stored_credentials(
            "user_1"
        ) == ("x", "x", None)

    def test_missing_item_raises_reauth(self):
        table = MagicMock()
        table.get_item.return_value = {}
        with pytest.raises(ESPNReauthRequired):
            _client(table=table).get_stored_credentials("user_1")


class TestMarkAuthFailed:
    def test_flags_matching_version(self):
        table = MagicMock()
        assert _client(table=table).mark_auth_failed("user_1", 1700) is True

        kwargs = table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "USER#user_1", "SK": "ESPN_CREDENTIALS"}
        assert kwargs["UpdateExpression"] == "SET auth_failed_at = :f"
        assert kwargs["ConditionExpression"] == (
            "attribute_exists(PK) AND updated_at = :u"
        )
        assert kwargs["ExpressionAttributeValues"][":u"] == 1700
        assert kwargs["ExpressionAttributeValues"][":f"]

    def test_replaced_or_missing_item_not_flagged(self):
        table = MagicMock()
        table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
        )
        assert _client(table=table).mark_auth_failed("user_1", 1700) is False

    def test_other_client_error_raises(self):
        table = MagicMock()
        table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}}, "UpdateItem"
        )
        with pytest.raises(botocore.exceptions.ClientError):
            _client(table=table).mark_auth_failed("user_1", 1700)

    def test_unknown_version_is_noop(self):
        table = MagicMock()
        assert _client(table=table).mark_auth_failed("user_1", None) is False
        table.update_item.assert_not_called()


class TestDeleteCredentials:
    def test_deletes_item_by_key(self):
        table = MagicMock()
        client = _client(table=table)

        client.delete_credentials("user_1")

        table.delete_item.assert_called_once_with(
            Key={"PK": "USER#user_1", "SK": "ESPN_CREDENTIALS"}
        )


class TestGetCredentialItem:
    def test_returns_item(self):
        table = MagicMock()
        table.get_item.return_value = {"Item": {"PK": "USER#user_1"}}
        assert _client(table=table).get_credential_item("user_1") == {
            "PK": "USER#user_1"
        }

    def test_client_error_returns_none(self):
        table = MagicMock()
        table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "X"}}, "GetItem"
        )
        assert _client(table=table).get_credential_item("user_1") is None


class TestFromEnv:
    def test_builds_client_from_env(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        monkeypatch.setenv("ESPN_KMS_REGION", "us-east-1")
        monkeypatch.setenv("ESPN_KMS_KEY_ID", "key-abc")

        mock_resource = MagicMock()
        mock_kms = MagicMock()
        with (
            patch("boto3.resource", return_value=mock_resource) as res,
            patch("boto3.client", return_value=mock_kms) as cli,
        ):
            client = espn_credentials.from_env()

        assert isinstance(client, EspnCredentialClient)
        res.return_value.Table.assert_called_once_with("test-table")
        # KMS client is pinned to the credential key's region (cross-region decrypt).
        cli.assert_any_call("kms", region_name="us-east-1")
