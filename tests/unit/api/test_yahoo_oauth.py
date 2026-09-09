"""Unit tests for the Yahoo OAuth helpers (src/api/yahoo_oauth.py)."""

import time
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest


@pytest.fixture
def yahoo():
    import yahoo_oauth

    return yahoo_oauth


@pytest.fixture
def mock_table():
    with patch("main.table") as mock:
        yield mock


@pytest.fixture
def mock_kms():
    with patch("main.kms_client") as mock, patch("main.YAHOO_KMS_KEY_ID", "key-123"):
        yield mock


@pytest.fixture
def mock_http():
    with patch("main.http_requests") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_credentials():
    """Stub the SSM-backed client credentials so no secret lookup runs."""
    with patch(
        "yahoo_oauth.get_secret_from_env_param",
        side_effect=lambda name: {
            "YAHOO_CLIENT_ID_SSM_PARAM": "client-id",
            "YAHOO_CLIENT_SECRET_SSM_PARAM": "client-secret",
        }[name],
    ) as mock:
        yield mock


class TestCreateOauthState:
    def test_persists_item_and_returns_state(self, yahoo, mock_table):
        state, code_challenge = yahoo.create_oauth_state("user_1", "45.l.678")

        assert isinstance(state, str) and state
        assert isinstance(code_challenge, str) and code_challenge
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == f"OAUTH_STATE#{state}"
        assert item["SK"] == "YAHOO"
        assert item["clerk_user_id"] == "user_1"
        assert item["league_id"] == "45.l.678"
        # The PKCE verifier is stored server-side (its S256 hash is the returned challenge).
        assert item["code_verifier"]
        assert item["code_verifier"] != code_challenge
        # TTL and expiry are set roughly OAUTH_STATE_TTL_SECONDS into the future.
        assert item["ttl"] == item["expires_at"]
        assert item["expires_at"] > int(time.time())

    def test_pkce_challenge_is_s256_of_verifier(self, yahoo, mock_table):
        import base64
        import hashlib

        _, code_challenge = yahoo.create_oauth_state("user_1", "x")
        verifier = mock_table.put_item.call_args.kwargs["Item"]["code_verifier"]
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        assert code_challenge == expected


class TestConsumeOauthState:
    def test_valid_state_returns_payload_and_deletes(self, yahoo, mock_table):
        mock_table.get_item.return_value = {
            "Item": {
                "clerk_user_id": "user_1",
                "league_id": "45.l.678",
                "code_verifier": "verifier-abc",
                "expires_at": int(time.time()) + 300,
            }
        }

        result = yahoo.consume_oauth_state("abc")

        assert result == {
            "clerk_user_id": "user_1",
            "league_id": "45.l.678",
            "code_verifier": "verifier-abc",
        }
        mock_table.delete_item.assert_called_once_with(
            Key={"PK": "OAUTH_STATE#abc", "SK": "YAHOO"}
        )

    def test_empty_state_returns_none(self, yahoo, mock_table):
        assert yahoo.consume_oauth_state("") is None
        mock_table.get_item.assert_not_called()

    def test_missing_item_returns_none(self, yahoo, mock_table):
        mock_table.get_item.return_value = {}
        assert yahoo.consume_oauth_state("abc") is None

    def test_expired_state_returns_none(self, yahoo, mock_table):
        mock_table.get_item.return_value = {
            "Item": {
                "clerk_user_id": "user_1",
                "league_id": "x",
                "expires_at": int(time.time()) - 1,
            }
        }
        assert yahoo.consume_oauth_state("abc") is None

    def test_get_client_error_returns_none(self, yahoo, mock_table):
        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "X"}}, "GetItem"
        )
        assert yahoo.consume_oauth_state("abc") is None

    def test_delete_client_error_still_returns_payload(self, yahoo, mock_table):
        mock_table.get_item.return_value = {
            "Item": {
                "clerk_user_id": "user_1",
                "league_id": "x",
                "expires_at": int(time.time()) + 300,
            }
        }
        mock_table.delete_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "X"}}, "DeleteItem"
        )
        assert yahoo.consume_oauth_state("abc") == {
            "clerk_user_id": "user_1",
            "league_id": "x",
            "code_verifier": "",
        }


class TestBuildAuthorizeUrl:
    def test_contains_oauth_params(self, yahoo):
        with patch("main.YAHOO_REDIRECT_URI", "https://api.example.com/cb"):
            url = yahoo.build_authorize_url("state-xyz", "challenge-abc")

        assert url.startswith("https://api.login.yahoo.com/oauth2/request_auth?")
        assert "client_id=client-id" in url
        assert "response_type=code" in url
        assert "state=state-xyz" in url
        assert "redirect_uri=https%3A%2F%2Fapi.example.com%2Fcb" in url
        assert "code_challenge=challenge-abc" in url
        assert "code_challenge_method=S256" in url


class TestExchangeCodeForTokens:
    def test_posts_and_returns_json(self, yahoo, mock_http):
        mock_http.post.return_value = MagicMock(
            **{"json.return_value": {"access_token": "at", "refresh_token": "rt"}}
        )
        with patch("main.YAHOO_REDIRECT_URI", "https://api.example.com/cb"):
            result = yahoo.exchange_code_for_tokens("the-code", "verifier-xyz")

        assert result == {"access_token": "at", "refresh_token": "rt"}
        args, kwargs = mock_http.post.call_args
        assert args[0] == "https://api.login.yahoo.com/oauth2/get_token"
        assert kwargs["data"]["grant_type"] == "authorization_code"
        assert kwargs["data"]["code"] == "the-code"
        assert kwargs["data"]["code_verifier"] == "verifier-xyz"
        assert kwargs["headers"]["Authorization"].startswith("Basic ")

    def test_raises_on_http_error(self, yahoo, mock_http):
        resp = MagicMock()
        resp.raise_for_status.side_effect = RuntimeError("boom")
        mock_http.post.return_value = resp
        with pytest.raises(RuntimeError):
            yahoo.exchange_code_for_tokens("bad", "verifier")


class TestRefreshTokens:
    def test_returns_json_on_success(self, yahoo, mock_http):
        mock_http.post.return_value = MagicMock(
            status_code=200,
            **{"json.return_value": {"access_token": "new"}},
        )
        result = yahoo.refresh_tokens("rt")
        assert result == {"access_token": "new"}

    def test_invalid_grant_raises_reauth(self, yahoo, mock_http):
        mock_http.post.return_value = MagicMock(
            status_code=400, text='{"error":"invalid_grant"}'
        )
        with pytest.raises(yahoo.YahooReauthRequired):
            yahoo.refresh_tokens("revoked")

    def test_other_400_raises_http_error(self, yahoo, mock_http):
        resp = MagicMock(status_code=400, text="something else")
        resp.raise_for_status.side_effect = RuntimeError("boom")
        mock_http.post.return_value = resp
        with pytest.raises(RuntimeError):
            yahoo.refresh_tokens("rt")


class TestEncryptDecrypt:
    def test_roundtrip(self, yahoo, mock_kms):
        mock_kms.encrypt.return_value = {"CiphertextBlob": b"cipher"}
        mock_kms.decrypt.return_value = {"Plaintext": b"secret-token"}

        ciphertext = yahoo._encrypt("secret-token")
        assert isinstance(ciphertext, str)
        mock_kms.encrypt.assert_called_once_with(
            KeyId="key-123", Plaintext=b"secret-token"
        )

        plaintext = yahoo._decrypt(ciphertext)
        assert plaintext == "secret-token"


class TestStoreTokens:
    def test_encrypts_and_persists(self, yahoo, mock_table, mock_kms):
        mock_kms.encrypt.side_effect = [
            {"CiphertextBlob": b"enc-access"},
            {"CiphertextBlob": b"enc-refresh"},
        ]

        tokens = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
        yahoo.store_tokens("user_1", tokens)

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "USER#user_1"
        assert item["SK"] == "YAHOO_OAUTH"
        # The stored token fields are ciphertext, never the plaintext tokens.
        assert item["access_token"] != tokens["access_token"]
        assert item["refresh_token"] != tokens["refresh_token"]
        assert item["expires_at"] > int(time.time())


class TestHasValidLink:
    def test_true_when_item_present(self, yahoo, mock_table):
        mock_table.get_item.return_value = {"Item": {"PK": "USER#user_1"}}
        assert yahoo.has_valid_link("user_1") is True

    def test_false_when_absent(self, yahoo, mock_table):
        mock_table.get_item.return_value = {}
        assert yahoo.has_valid_link("user_1") is False

    def test_false_on_client_error(self, yahoo, mock_table):
        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "X"}}, "GetItem"
        )
        assert yahoo.has_valid_link("user_1") is False


class TestGetValidAccessToken:
    def test_returns_decrypted_when_not_expired(self, yahoo, mock_table, mock_kms):
        mock_table.get_item.return_value = {
            "Item": {
                "access_token": "ZW5j",  # valid base64 ("enc")
                "refresh_token": "ZW5j",
                "expires_at": int(time.time()) + 3600,
            }
        }
        mock_kms.decrypt.return_value = {"Plaintext": b"live-access"}

        assert yahoo.get_valid_access_token("user_1") == "live-access"
        mock_kms.decrypt.assert_called_once()

    def test_refreshes_when_expired(self, yahoo, mock_table, mock_kms, mock_http):
        mock_table.get_item.return_value = {
            "Item": {
                "access_token": "ZW5j",  # valid base64 ("enc")
                "refresh_token": "ZW5j",
                "expires_at": int(time.time()) - 10,
            }
        }
        mock_kms.decrypt.return_value = {"Plaintext": b"old-refresh"}
        mock_kms.encrypt.side_effect = [
            {"CiphertextBlob": b"a"},
            {"CiphertextBlob": b"b"},
        ]
        mock_http.post.return_value = MagicMock(
            status_code=200,
            **{
                "json.return_value": {
                    "access_token": "fresh-access",
                    "refresh_token": "new-rt",
                    "expires_in": 3600,
                }
            },
        )

        assert yahoo.get_valid_access_token("user_1") == "fresh-access"
        mock_table.put_item.assert_called_once()  # persisted the refreshed tokens

    def test_raises_reauth_when_no_link(self, yahoo, mock_table):
        mock_table.get_item.return_value = {}
        with pytest.raises(yahoo.YahooReauthRequired):
            yahoo.get_valid_access_token("user_1")
