"""Shared ESPN cookie storage (backend/espn-credential-storage).

Persists a user's ESPN ``SWID`` and ``espn_s2`` cookies KMS-encrypted at rest so the scheduled
refresh Lambda can refresh that user's ESPN leagues on their behalf when they opt into automatic
refresh. This mirrors ``common.yahoo_tokens`` — dependencies are injected so the same engine runs
in the API Lambda (clients from ``main.*``) and the onboarder Lambda (clients from ``from_env()``).

Unlike Yahoo OAuth, ESPN offers no programmatic refresh: an ``espn_s2`` cookie simply expires, at
which point a scheduled refresh surfaces the existing ``ESPN_AUTH`` re-link signal. There is
therefore no refresh/PKCE logic here — only encrypt/decrypt, store, fetch, and delete.

Cookie values are KMS-encrypted at rest and never returned to the browser, logged, or traced.
"""

import base64
import logging
import time
from typing import Any

import botocore.exceptions

logger = logging.getLogger(__name__)


class ESPNReauthRequired(Exception):
    """No stored ESPN cookies exist for the user (or they were deleted).

    Surfaced to the onboarding/refresh flows as the ``ESPN_AUTH`` re-link signal, so a scheduled
    refresh with no usable cookies records that failure instead of proceeding without credentials.
    """


class EspnCredentialClient:
    """Encrypt/store/fetch engine for a user's ESPN ``SWID`` + ``espn_s2`` cookies.

    Dependencies are injected so the same logic runs in the API Lambda (clients from ``main.*``)
    and the onboarder Lambda (clients from ``from_env()``).

    Args:
        table: DynamoDB table resource holding the ``USER#{id} / ESPN_CREDENTIALS`` items.
        kms_client: boto3 KMS client used to encrypt/decrypt cookie values.
        kms_key_id: The credential KMS key id/ARN (shared with Yahoo tokens).
    """

    def __init__(self, *, table: Any, kms_client: Any, kms_key_id: str):
        self._table = table
        self._kms_client = kms_client
        self._kms_key_id = kms_key_id

    def encrypt(self, plaintext: str) -> str:
        """KMS-encrypt a cookie value, returning base64 ciphertext for DynamoDB storage."""
        result = self._kms_client.encrypt(
            KeyId=self._kms_key_id, Plaintext=plaintext.encode()
        )
        return base64.b64encode(result["CiphertextBlob"]).decode()

    def decrypt(self, ciphertext_b64: str) -> str:
        """KMS-decrypt base64 ciphertext back to the plaintext cookie value."""
        blob = base64.b64decode(ciphertext_b64)
        result = self._kms_client.decrypt(KeyId=self._kms_key_id, CiphertextBlob=blob)
        return result["Plaintext"].decode()

    def store_credentials(self, clerk_user_id: str, swid: str, espn_s2: str) -> None:
        """Persist an encrypted per-user ``ESPN_CREDENTIALS`` item.

        Both cookie values are KMS-encrypted. Item key:
        ``PK=USER#{clerk_user_id}, SK=ESPN_CREDENTIALS``. A later store replaces the prior values.
        """
        now = int(time.time())
        self._table.put_item(
            Item={
                "PK": f"USER#{clerk_user_id}",
                "SK": "ESPN_CREDENTIALS",
                "swid": self.encrypt(swid),
                "espn_s2": self.encrypt(espn_s2),
                "updated_at": now,
            }
        )

    def get_credentials(self, clerk_user_id: str) -> tuple[str, str]:
        """Return a user's decrypted ``(swid, espn_s2)``.

        Raises:
            ESPNReauthRequired: when the user has no stored ``ESPN_CREDENTIALS`` item.
        """
        item = self.get_credential_item(clerk_user_id)
        if item is None:
            raise ESPNReauthRequired("No stored ESPN cookies for user")
        return self.decrypt(item["swid"]), self.decrypt(item["espn_s2"])

    def delete_credentials(self, clerk_user_id: str) -> None:
        """Delete a user's stored ``ESPN_CREDENTIALS`` item.

        Idempotent: DynamoDB ``delete_item`` is a no-op when the item is absent, so deleting for a
        user with no stored cookies succeeds silently. Used when the user no longer has any ESPN
        league opted into automatic refresh (backend/espn-credential-storage).
        """
        self._table.delete_item(
            Key={"PK": f"USER#{clerk_user_id}", "SK": "ESPN_CREDENTIALS"}
        )

    def get_credential_item(self, clerk_user_id: str) -> dict[str, Any] | None:
        """Read the raw (still-encrypted) ``ESPN_CREDENTIALS`` item for a user, or ``None``."""
        try:
            response = self._table.get_item(
                Key={"PK": f"USER#{clerk_user_id}", "SK": "ESPN_CREDENTIALS"}
            )
        except botocore.exceptions.ClientError as e:
            logger.error("Failed to read ESPN credential item: %s", e)
            return None
        return response.get("Item")


def from_env() -> EspnCredentialClient:
    """Build an ``EspnCredentialClient`` from environment configuration.

    Used by the onboarder Lambda, which has no ``main`` module. The KMS client is pinned to
    ``ESPN_KMS_REGION`` so decrypt works regardless of the Lambda's own region; the key
    (``ESPN_KMS_KEY_ID``) is the credential KMS key shared with Yahoo tokens.
    """
    import os

    import boto3

    table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE_NAME"])
    kms_client = boto3.client("kms", region_name=os.environ["ESPN_KMS_REGION"])
    return EspnCredentialClient(
        table=table,
        kms_client=kms_client,
        kms_key_id=os.environ["ESPN_KMS_KEY_ID"],
    )
