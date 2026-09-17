"""Shared Yahoo OAuth token management (backend/yahoo-oauth).

The token *engine* — encrypt/decrypt, refresh, store, and the transparent
``get_valid_access_token`` — lives here so both the API Lambda (which owns the
authorize/callback handshake in ``api/yahoo_oauth.py``) and the onboarder Lambda
(the Yahoo data client) can obtain and refresh a caller's Yahoo access token.

Rather than reaching a specific ``main`` module for AWS clients, the engine takes
its dependencies explicitly (``YahooTokenClient``), so:

* ``api/yahoo_oauth.py`` builds one from ``main.*`` at call time (test patches on
  ``main.*`` keep working), and
* the onboarder builds one from its own environment via ``from_env()`` — including a
  KMS client pinned to ``YAHOO_KMS_REGION`` so cross-region decrypt works regardless
  of the onboarder Lambda's region.

Access and refresh tokens are KMS-encrypted at rest and never returned to the browser.
"""

import base64
import logging
import os
import time
from collections.abc import Callable
from typing import Any

import botocore.exceptions

logger = logging.getLogger(__name__)

YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"  # noqa: S105  URL, not a secret

# Refresh the access token when it is within this many seconds of its 1-hour expiry,
# so a data call never races the boundary.
TOKEN_EXPIRY_SKEW_SECONDS = 120


class YahooReauthRequired(Exception):
    """The stored Yahoo link is missing or its refresh token was revoked.

    Surfaced to the onboarding/refresh flows as the ``YAHOO_AUTH`` re-link signal.
    """


class YahooTokenClient:
    """Encrypt/refresh/store engine for a user's Yahoo OAuth tokens.

    Dependencies are injected so the same logic runs in the API Lambda (clients from
    ``main.*``) and the onboarder Lambda (clients from ``from_env()``).

    Args:
        table: DynamoDB table resource holding the ``USER#{id} / YAHOO_OAUTH`` items.
        kms_client: boto3 KMS client used to encrypt/decrypt token values.
        kms_key_id: The Yahoo token KMS key id/ARN.
        http_requests: The ``requests``-like module used for token POSTs.
        redirect_uri: The registered OAuth redirect URI (sent on a refresh grant).
        client_id_provider: Callable returning the Yahoo ``client_id`` (PKCE public
            client — no client_secret).
        token_url: Yahoo token endpoint (overridable for tests).
    """

    def __init__(
        self,
        *,
        table: Any,
        kms_client: Any,
        kms_key_id: str,
        http_requests: Any,
        redirect_uri: str,
        client_id_provider: Callable[[], str],
        token_url: str = YAHOO_TOKEN_URL,
    ):
        self._table = table
        self._kms_client = kms_client
        self._kms_key_id = kms_key_id
        self._http = http_requests
        self._redirect_uri = redirect_uri
        self._client_id_provider = client_id_provider
        self._token_url = token_url

    def encrypt(self, plaintext: str) -> str:
        """KMS-encrypt a token value, returning base64 ciphertext for DynamoDB storage."""
        result = self._kms_client.encrypt(
            KeyId=self._kms_key_id, Plaintext=plaintext.encode()
        )
        return base64.b64encode(result["CiphertextBlob"]).decode()

    def decrypt(self, ciphertext_b64: str) -> str:
        """KMS-decrypt base64 ciphertext back to the plaintext token value."""
        blob = base64.b64decode(ciphertext_b64)
        result = self._kms_client.decrypt(KeyId=self._kms_key_id, CiphertextBlob=blob)
        return result["Plaintext"].decode()

    def refresh_tokens(self, refresh_token: str) -> dict[str, Any]:
        """Mint a fresh access token from a stored ``refresh_token``.

        Raises:
            YahooReauthRequired: when Yahoo returns ``invalid_grant`` (revoked refresh token).
            requests.RequestException: on other network failures.
        """
        data = {
            "client_id": self._client_id_provider(),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        if self._redirect_uri:
            data["redirect_uri"] = self._redirect_uri
        response = self._http.post(
            self._token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if response.status_code == 400 and "invalid_grant" in response.text:
            raise YahooReauthRequired("Yahoo refresh token was revoked")
        response.raise_for_status()
        return response.json()

    def store_tokens(self, clerk_user_id: str, token_response: dict[str, Any]) -> None:
        """Persist an encrypted per-user ``YAHOO_OAUTH`` token item.

        Access and refresh tokens are KMS-encrypted; ``expires_at`` is computed from
        Yahoo's ``expires_in`` (1-hour lifetime). Item key:
        ``PK=USER#{clerk_user_id}, SK=YAHOO_OAUTH``.
        """
        now = int(time.time())
        expires_in = int(token_response.get("expires_in", 3600))
        self._table.put_item(
            Item={
                "PK": f"USER#{clerk_user_id}",
                "SK": "YAHOO_OAUTH",
                "access_token": self.encrypt(token_response["access_token"]),
                "refresh_token": self.encrypt(token_response["refresh_token"]),
                "token_type": token_response.get("token_type", "bearer"),
                "expires_at": now + expires_in,
                "updated_at": now,
            }
        )

    def get_token_item(self, clerk_user_id: str) -> dict[str, Any] | None:
        """Read the raw (still-encrypted) ``YAHOO_OAUTH`` item for a user, or ``None``."""
        try:
            response = self._table.get_item(
                Key={"PK": f"USER#{clerk_user_id}", "SK": "YAHOO_OAUTH"}
            )
        except botocore.exceptions.ClientError as e:
            logger.error("Failed to read Yahoo token item: %s", e)
            return None
        return response.get("Item")

    def has_valid_link(self, clerk_user_id: str) -> bool:
        """Return whether the caller has a stored Yahoo link (the onboarding gate).

        A stored item means the account is linked; a revoked refresh token only surfaces
        later, at data-fetch time, as the ``YAHOO_AUTH`` re-link signal.
        """
        return self.get_token_item(clerk_user_id) is not None

    def get_valid_access_token(self, clerk_user_id: str) -> str:
        """Return a currently-valid Yahoo access token for the caller, refreshing if needed.

        Refreshes proactively when within the expiry skew (not only on a 401).

        Raises:
            YahooReauthRequired: when no link exists or the refresh token was revoked.
        """
        item = self.get_token_item(clerk_user_id)
        if item is None:
            raise YahooReauthRequired("No Yahoo link for user")
        if int(item["expires_at"]) - TOKEN_EXPIRY_SKEW_SECONDS > int(time.time()):
            return self.decrypt(item["access_token"])
        refreshed = self.refresh_tokens(self.decrypt(item["refresh_token"]))
        self.store_tokens(clerk_user_id, refreshed)
        return refreshed["access_token"]


def from_env() -> YahooTokenClient:
    """Build a ``YahooTokenClient`` from environment configuration.

    Used by the onboarder Lambda, which has no ``main`` module. The KMS client is pinned
    to ``YAHOO_KMS_REGION`` so decrypt works regardless of the Lambda's own region, and
    the ``client_id`` is resolved from its SecureString SSM parameter at call time.
    """
    import boto3
    import requests

    from common.secrets import get_secret_from_env_param

    table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE_NAME"])
    kms_client = boto3.client("kms", region_name=os.environ["YAHOO_KMS_REGION"])
    return YahooTokenClient(
        table=table,
        kms_client=kms_client,
        kms_key_id=os.environ["YAHOO_KMS_KEY_ID"],
        http_requests=requests,
        redirect_uri=os.environ.get("YAHOO_REDIRECT_URI", ""),
        client_id_provider=lambda: get_secret_from_env_param(
            "YAHOO_CLIENT_ID_SSM_PARAM"
        ),
    )
