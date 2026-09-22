"""API-side helpers for the stored ESPN credential item (backend/espn-credential-storage).

The encrypt/store/fetch engine lives in the shared ``common.espn_credentials`` module so the
onboarder Lambda can reuse it. The API only needs to *delete* a user's stored ESPN cookies (on
opt-out or when their last opted-in ESPN league is removed) — the onboarder is what stores them
after a successful opted-in fetch. This thin wrapper builds the engine from ``main.*`` AWS clients
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
