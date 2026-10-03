"""API-side helpers for the stored ESPN credential item (backend/espn-credential-storage).

The encrypt/store/fetch engine lives in the shared ``common.espn_credentials`` module so the
onboarder Lambda can reuse it. The API deletes a user's stored ESPN cookies (on opt-out or when
their last opted-in ESPN league is removed) and stores them when an opted-in refresh is blocked
(cooldown / up to date / in progress) after validating them against ESPN; otherwise the onboarder
stores them after a successful opted-in fetch. This thin wrapper builds the engine from ``main.*`` AWS clients
at call time so test patches on ``main.table`` / ``main.kms_client`` stay effective.
"""

import main

from common.espn_credentials import EspnCredentialClient


def _credential_client() -> EspnCredentialClient:
    """Build the shared ESPN credential engine from ``main.*`` AWS clients at call time."""
    return EspnCredentialClient(
        table=main.table,
        kms_client=main.kms_client,
        kms_key_id=main.ESPN_KMS_KEY_ID,
    )


def delete_credentials(clerk_user_id: str) -> None:
    """Delete a user's stored ``ESPN_CREDENTIALS`` item (idempotent)."""
    _credential_client().delete_credentials(clerk_user_id)


def store_credentials(clerk_user_id: str, swid: str, espn_s2: str) -> None:
    """Persist a user's ESPN cookies encrypted at rest, replacing any prior values."""
    _credential_client().store_credentials(clerk_user_id, swid, espn_s2)
