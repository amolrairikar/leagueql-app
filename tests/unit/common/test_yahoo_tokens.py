"""Tests for the shared Yahoo token engine (src/common/yahoo_tokens.py)."""

import threading
import time
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from common import yahoo_tokens
from common.yahoo_tokens import (
    CachedAccessToken,
    YahooReauthRequired,
    YahooTokenClient,
)


def _client(**overrides):
    """Build a YahooTokenClient with MagicMock deps, overridable per test."""
    deps = {
        "table": MagicMock(),
        "kms_client": MagicMock(),
        "kms_key_id": "key-123",
        "http_requests": MagicMock(),
        "redirect_uri": "https://api.example.com/cb",
        "client_id_provider": lambda: "client-id",
    }
    deps.update(overrides)
    return YahooTokenClient(**deps)


class TestEncryptDecrypt:
    def test_roundtrip(self):
        kms = MagicMock()
        kms.encrypt.return_value = {"CiphertextBlob": b"cipher"}
        kms.decrypt.return_value = {"Plaintext": b"secret-token"}
        client = _client(kms_client=kms)

        ciphertext = client.encrypt("secret-token")
        assert isinstance(ciphertext, str)
        kms.encrypt.assert_called_once_with(KeyId="key-123", Plaintext=b"secret-token")

        assert client.decrypt(ciphertext) == "secret-token"


class TestRefreshTokens:
    def test_returns_json_on_success(self):
        http = MagicMock()
        http.post.return_value = MagicMock(
            status_code=200, **{"json.return_value": {"access_token": "new"}}
        )
        client = _client(http_requests=http)

        assert client.refresh_tokens("rt") == {"access_token": "new"}
        args, kwargs = http.post.call_args
        assert args[0] == yahoo_tokens.YAHOO_TOKEN_URL
        assert kwargs["data"]["grant_type"] == "refresh_token"
        assert kwargs["data"]["client_id"] == "client-id"
        assert kwargs["data"]["redirect_uri"] == "https://api.example.com/cb"
        assert "client_secret" not in kwargs["data"]

    def test_omits_redirect_uri_when_unset(self):
        http = MagicMock()
        http.post.return_value = MagicMock(status_code=200, **{"json.return_value": {}})
        client = _client(http_requests=http, redirect_uri="")

        client.refresh_tokens("rt")
        assert "redirect_uri" not in http.post.call_args.kwargs["data"]

    def test_invalid_grant_raises_reauth(self):
        http = MagicMock()
        http.post.return_value = MagicMock(
            status_code=400, text='{"error":"invalid_grant"}'
        )
        client = _client(http_requests=http)

        with pytest.raises(YahooReauthRequired):
            client.refresh_tokens("revoked")

    def test_other_400_raises_http_error(self):
        resp = MagicMock(status_code=400, text="something else")
        resp.raise_for_status.side_effect = RuntimeError("boom")
        http = MagicMock()
        http.post.return_value = resp
        client = _client(http_requests=http)

        with pytest.raises(RuntimeError):
            client.refresh_tokens("rt")


class TestStoreTokens:
    def test_encrypts_and_persists(self):
        table = MagicMock()
        kms = MagicMock()
        kms.encrypt.side_effect = [
            {"CiphertextBlob": b"enc-access"},
            {"CiphertextBlob": b"enc-refresh"},
        ]
        client = _client(table=table, kms_client=kms)

        tokens = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
        client.store_tokens("user_1", tokens)

        item = table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "USER#user_1"
        assert item["SK"] == "YAHOO_OAUTH"
        # Stored token fields are ciphertext, never the plaintext tokens.
        assert item["access_token"] != tokens["access_token"]
        assert item["refresh_token"] != tokens["refresh_token"]
        assert item["token_type"] == "bearer"  # noqa: S105 — asserting a token type, not a secret
        assert item["expires_at"] > int(time.time())

    def test_defaults_expiry_when_absent(self):
        table = MagicMock()
        kms = MagicMock()
        kms.encrypt.side_effect = [
            {"CiphertextBlob": b"a"},
            {"CiphertextBlob": b"b"},
        ]
        client = _client(table=table, kms_client=kms)

        client.store_tokens("user_1", {"access_token": "at", "refresh_token": "rt"})
        item = table.put_item.call_args.kwargs["Item"]
        # Defaults to a 1-hour lifetime (~3600s) when expires_in is omitted.
        assert item["expires_at"] - int(time.time()) > 3000


class TestDeleteTokens:
    def test_deletes_item_by_key(self):
        table = MagicMock()
        client = _client(table=table)

        client.delete_tokens("user_1")

        table.delete_item.assert_called_once_with(
            Key={"PK": "USER#user_1", "SK": "YAHOO_OAUTH"}
        )


class TestGetTokenItemAndHasValidLink:
    def test_get_token_item_returns_item(self):
        table = MagicMock()
        table.get_item.return_value = {"Item": {"PK": "USER#user_1"}}
        client = _client(table=table)

        assert client.get_token_item("user_1") == {"PK": "USER#user_1"}

    def test_get_token_item_client_error_returns_none(self):
        table = MagicMock()
        table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "X"}}, "GetItem"
        )
        client = _client(table=table)

        assert client.get_token_item("user_1") is None

    def test_has_valid_link_true_when_present(self):
        table = MagicMock()
        table.get_item.return_value = {"Item": {"PK": "USER#user_1"}}
        assert _client(table=table).has_valid_link("user_1") is True

    def test_has_valid_link_false_when_absent(self):
        table = MagicMock()
        table.get_item.return_value = {}
        assert _client(table=table).has_valid_link("user_1") is False


class TestGetValidAccessToken:
    def test_returns_decrypted_when_not_expired(self):
        table = MagicMock()
        table.get_item.return_value = {
            "Item": {
                "access_token": "ZW5j",  # base64 ("enc")
                "refresh_token": "ZW5j",
                "expires_at": int(time.time()) + 3600,
            }
        }
        kms = MagicMock()
        kms.decrypt.return_value = {"Plaintext": b"live-access"}
        client = _client(table=table, kms_client=kms)

        assert client.get_valid_access_token("user_1") == "live-access"
        kms.decrypt.assert_called_once()

    def test_refreshes_when_expired(self):
        table = MagicMock()
        table.get_item.return_value = {
            "Item": {
                "access_token": "ZW5j",
                "refresh_token": "ZW5j",
                "expires_at": int(time.time()) - 10,
            }
        }
        kms = MagicMock()
        kms.decrypt.return_value = {"Plaintext": b"old-refresh"}
        kms.encrypt.side_effect = [{"CiphertextBlob": b"a"}, {"CiphertextBlob": b"b"}]
        http = MagicMock()
        http.post.return_value = MagicMock(
            status_code=200,
            **{
                "json.return_value": {
                    "access_token": "fresh-access",
                    "refresh_token": "new-rt",
                    "expires_in": 3600,
                }
            },
        )
        client = _client(table=table, kms_client=kms, http_requests=http)

        assert client.get_valid_access_token("user_1") == "fresh-access"
        table.put_item.assert_called_once()

    def test_raises_reauth_when_no_link(self):
        table = MagicMock()
        table.get_item.return_value = {}
        with pytest.raises(YahooReauthRequired):
            _client(table=table).get_valid_access_token("user_1")


class TestGetValidAccessTokenWithExpiry:
    def test_returns_stored_expiry_when_not_expired(self):
        expires_at = int(time.time()) + 3600
        table = MagicMock()
        table.get_item.return_value = {
            "Item": {
                "access_token": "ZW5j",
                "refresh_token": "ZW5j",
                "expires_at": expires_at,
            }
        }
        kms = MagicMock()
        kms.decrypt.return_value = {"Plaintext": b"live"}
        client = _client(table=table, kms_client=kms)

        assert client.get_valid_access_token_with_expiry("u") == ("live", expires_at)

    def test_returns_new_expiry_after_refresh(self):
        table = MagicMock()
        table.get_item.return_value = {
            "Item": {
                "access_token": "ZW5j",
                "refresh_token": "ZW5j",
                "expires_at": int(time.time()) - 10,
            }
        }
        kms = MagicMock()
        kms.decrypt.return_value = {"Plaintext": b"old-refresh"}
        kms.encrypt.return_value = {"CiphertextBlob": b"x"}
        http = MagicMock()
        http.post.return_value = MagicMock(
            status_code=200,
            **{
                "json.return_value": {
                    "access_token": "fresh",
                    "refresh_token": "rt2",
                    "expires_in": 1800,
                }
            },
        )
        client = _client(table=table, kms_client=kms, http_requests=http)

        token, expires_at = client.get_valid_access_token_with_expiry("u")
        assert token == "fresh"  # noqa: S105
        assert abs(expires_at - (int(time.time()) + 1800)) <= 2

    def test_raises_reauth_when_no_link(self):
        table = MagicMock()
        table.get_item.return_value = {}
        with pytest.raises(YahooReauthRequired):
            _client(table=table).get_valid_access_token_with_expiry("u")


def _fake_token_client(tokens_by_user=None, ttl=3600):
    """A token client whose resolved token is ``tok-<user>-<n>`` (n = resolution count)."""
    client = MagicMock()
    counts: dict[str, int] = {}

    def resolve(user):
        counts[user] = counts.get(user, 0) + 1
        return f"tok-{user}-{counts[user]}", int(time.time()) + ttl

    client.get_valid_access_token_with_expiry.side_effect = resolve
    return client


class TestCachedAccessToken:
    def test_reuses_token_within_validity(self):
        client = _fake_token_client()
        cache = CachedAccessToken(client, "u")

        assert [cache.get() for _ in range(5)] == ["tok-u-1"] * 5
        assert client.get_valid_access_token_with_expiry.call_count == 1

    def test_resolves_again_inside_expiry_skew(self):
        client = _fake_token_client(ttl=yahoo_tokens.TOKEN_EXPIRY_SKEW_SECONDS - 1)
        cache = CachedAccessToken(client, "u")

        assert cache.get() == "tok-u-1"
        assert cache.get() == "tok-u-2"

    def test_resolves_again_after_expiry_passes(self):
        client = _fake_token_client()
        cache = CachedAccessToken(client, "u")
        cache.get()
        with patch.object(yahoo_tokens.time, "time", return_value=time.time() + 3600):
            assert cache.get() == "tok-u-2"

    def test_invalidate_rejected_token_forces_resolution(self):
        client = _fake_token_client()
        cache = CachedAccessToken(client, "u")
        rejected = cache.get()

        cache.invalidate(rejected)

        assert cache.get() == "tok-u-2"

    def test_invalidate_stale_token_is_noop(self):
        client = _fake_token_client()
        cache = CachedAccessToken(client, "u")
        stale = cache.get()
        cache.invalidate(stale)
        fresh = cache.get()

        cache.invalidate(stale)  # another request rejected the same stale token

        assert cache.get() == fresh
        assert client.get_valid_access_token_with_expiry.call_count == 2

    def test_failure_is_not_cached(self):
        client = MagicMock()
        client.get_valid_access_token_with_expiry.side_effect = [
            YahooReauthRequired("revoked"),
            ("tok", int(time.time()) + 3600),
        ]
        cache = CachedAccessToken(client, "u")

        with pytest.raises(YahooReauthRequired):
            cache.get()
        assert cache.get() == "tok"

    def test_concurrent_gets_resolve_once(self):
        client = _fake_token_client()
        cache = CachedAccessToken(client, "u")
        results: list[str] = []
        barrier = threading.Barrier(8)

        def worker():
            barrier.wait()
            results.append(cache.get())

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results == ["tok-u-1"] * 8
        assert client.get_valid_access_token_with_expiry.call_count == 1


class TestCachedAccessTokenUserIsolation:
    def test_interleaved_users_only_see_their_own_token(self):
        client = _fake_token_client()
        a = CachedAccessToken(client, "user-a")
        b = CachedAccessToken(client, "user-b")

        seen_a = [a.get()]
        seen_b = [b.get()]
        a.invalidate(seen_a[0])  # a's token rejected -> a re-resolves, b untouched
        seen_a.append(a.get())
        seen_b.append(b.get())
        b.invalidate(seen_a[-1])  # a's token must not invalidate b's
        seen_b.append(b.get())

        assert seen_a == ["tok-user-a-1", "tok-user-a-2"]
        assert seen_b == ["tok-user-b-1", "tok-user-b-1", "tok-user-b-1"]
        users = [
            c.args[0] for c in client.get_valid_access_token_with_expiry.call_args_list
        ]
        assert users == ["user-a", "user-b", "user-a"]

    def test_module_holds_no_token_cache_state(self):
        cache_like = [
            name
            for name, value in vars(yahoo_tokens).items()
            if isinstance(value, dict | list | set) and not name.startswith("__")
        ]
        assert cache_like == []
        assert not [
            n for n, v in vars(CachedAccessToken).items() if isinstance(v, dict | list)
        ]


class TestFromEnv:
    def test_builds_client_from_env(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        monkeypatch.setenv("YAHOO_KMS_REGION", "us-east-1")
        monkeypatch.setenv("YAHOO_KMS_KEY_ID", "key-abc")
        monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://api.example.com/cb")

        mock_resource = MagicMock()
        mock_kms = MagicMock()
        with (
            patch("boto3.resource", return_value=mock_resource) as res,
            patch("boto3.client", return_value=mock_kms) as cli,
        ):
            client = yahoo_tokens.from_env()

        assert isinstance(client, YahooTokenClient)
        res.return_value.Table.assert_called_once_with("test-table")
        # KMS client is pinned to the Yahoo key's region (cross-region decrypt). Other
        # boto3.client calls (e.g. secrets' SSM client) may also occur on import.
        cli.assert_any_call("kms", region_name="us-east-1")
