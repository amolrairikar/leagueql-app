"""Mint a Clerk session JWT for the ESPN integration tests.

The deployed API Gateway JWT authorizer only accepts Clerk-signed tokens whose
``iss`` matches the instance issuer and whose ``aud`` matches the configured
audience. We mint such a token server-side with the instance secret key: create a
(testing-only) session for a fixed test user, then exchange it for a template
token. The ``aud`` claim is supplied by the ``CLERK_JWT_TEMPLATE`` JWT template
configured in the Clerk dashboard; ``iss``/``sub`` are Clerk default claims.

Tokens are short-lived, so callers should mint immediately before use.
"""

import requests

_CLERK_API_BASE = "https://api.clerk.com/v1"
_TIMEOUT = 30


def mint_jwt(secret_key: str, user_id: str, template: str) -> str:
    """Return a Clerk-signed JWT for ``user_id`` rendered from ``template``.

    Args:
        secret_key: Clerk instance secret key (``sk_...``).
        user_id: Clerk user the session/token is minted for (``user_...``). The
            delete endpoint has no ownership check, so any valid user works.
        template: Name of the Clerk JWT template that sets the ``aud`` claim.

    Returns:
        The encoded JWT string to send as a ``Bearer`` token.
    """
    headers = {"Authorization": f"Bearer {secret_key}"}

    # Testing-only session creation (not available on production instances).
    session_resp = requests.post(
        f"{_CLERK_API_BASE}/sessions",
        headers=headers,
        json={"user_id": user_id},
        timeout=_TIMEOUT,
    )
    session_resp.raise_for_status()
    session_id = session_resp.json()["id"]

    token_resp = requests.post(
        f"{_CLERK_API_BASE}/sessions/{session_id}/tokens/{template}",
        headers=headers,
        timeout=_TIMEOUT,
    )
    token_resp.raise_for_status()
    return token_resp.json()["jwt"]
