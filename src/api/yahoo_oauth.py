"""Yahoo OAuth 2.0 helpers for the LeagueQL API (backend/yahoo-oauth).

Implements the authorization-code handshake against Yahoo's login endpoints:

* ``build_authorize_url`` / ``create_oauth_state`` — start the flow (authorize route).
* ``consume_oauth_state`` + ``exchange_code_for_tokens`` + ``store_tokens`` — finish it
  (callback route).
* ``get_valid_access_token`` / ``refresh_tokens`` — transparent refresh for the future
  Yahoo data client.
* ``has_valid_link`` — the onboarding gate ("link Yahoo first").

AWS clients (``main.table``, ``main.kms_client``) and the HTTP module
(``main.http_requests``) are reached through ``main`` at call time so test patches on
``main.*`` take effect here. The Yahoo app is a **PKCE public client**: the ``client_id`` is
read from a SecureString SSM parameter (whose *name* lives in an env var) and no
``client_secret`` is used — Yahoo rejects a secret sent alongside a PKCE ``code_challenge``.
Access and refresh tokens are KMS-encrypted at rest and never returned to the browser.
"""

import base64
import hashlib
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import botocore.exceptions
import main
from main import logger

from common.secrets import get_secret_from_env_param

# The token engine (encrypt/refresh/store/get_valid_access_token) lives in a shared module
# so the onboarder Lambda can reuse it. These names are re-exported to preserve this module's
# public surface (backend/yahoo-oauth); the callback/authorize handshake below stays here.
from common.yahoo_tokens import (
    TOKEN_EXPIRY_SKEW_SECONDS,  # noqa: F401 — re-exported public surface
    YAHOO_TOKEN_URL,
    YahooReauthRequired,  # noqa: F401 — re-exported public surface
    YahooTokenClient,
)

YAHOO_AUTHORIZE_URL = "https://api.login.yahoo.com/oauth2/request_auth"

# Single-use state lives ~10 minutes — long enough for a user to complete the Yahoo
# consent screen, short enough to bound replay. The DynamoDB TTL reaps expired items;
# the code also rejects any state past its stored ``expires_at`` on read.
OAUTH_STATE_TTL_SECONDS = 600

# The onboarding gate reports this code so the frontend routes to the OAuth (re)link step
# rather than showing a generic failure.
YAHOO_AUTH_CODE = "YAHOO_AUTH"


def _token_client() -> YahooTokenClient:
    """Build the shared token engine from ``main.*`` AWS clients at call time.

    Reading ``main.*`` here (rather than at import) keeps test patches on ``main.table`` /
    ``main.kms_client`` / ``main.http_requests`` effective for the delegating helpers below.
    """
    return YahooTokenClient(
        table=main.table,
        kms_client=main.kms_client,
        kms_key_id=main.YAHOO_KMS_KEY_ID,
        http_requests=main.http_requests,
        redirect_uri=main.YAHOO_REDIRECT_URI,
        client_id_provider=_client_id,
    )


def _client_id() -> str:
    """Return the Yahoo Consumer Key (``client_id``) from its SecureString SSM parameter.

    Only the parameter *name* is in an env var; the value never enters the Lambda environment,
    Terraform state, or logs. This app is a PKCE public client, so no client_secret is used —
    Yahoo rejects a secret alongside a PKCE ``code_challenge``.
    """
    return get_secret_from_env_param("YAHOO_CLIENT_ID_SSM_PARAM")


def _generate_pkce() -> tuple[str, str]:
    """Return an ``(code_verifier, code_challenge)`` PKCE pair (RFC 7636, S256).

    Yahoo requires PKCE on the authorization request: the authorize URL carries the
    ``code_challenge`` (S256 of the verifier) and the token exchange sends the matching
    ``code_verifier``. The verifier is stored server-side with the OAuth state, never in the
    browser.
    """
    verifier = secrets.token_urlsafe(64)  # ~86 chars of RFC 7636 unreserved alphabet
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def create_oauth_state(clerk_user_id: str, league_id: str) -> tuple[str, str]:
    """Mint a single-use ``state`` + PKCE pair, bound to the caller and persisted with a TTL.

    Stores ``PK=OAUTH_STATE#{state}, SK=YAHOO`` carrying the caller's Clerk user id, the
    pending ``league_id``, and the PKCE ``code_verifier`` so the callback can validate the
    caller, resume onboarding, and complete the token exchange.

    Args:
        clerk_user_id: The authenticated caller the state is bound to.
        league_id: The Yahoo league id to resume onboarding for after the callback.

    Returns:
        ``(state, code_challenge)`` — the ``state`` and PKCE ``code_challenge`` to embed in
        the Yahoo consent URL.
    """
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce()
    now = int(time.time())
    main.table.put_item(
        Item={
            "PK": f"OAUTH_STATE#{state}",
            "SK": "YAHOO",
            "clerk_user_id": clerk_user_id,
            "league_id": league_id,
            "code_verifier": code_verifier,
            "created_at": now,
            "expires_at": now + OAUTH_STATE_TTL_SECONDS,
            "ttl": now + OAUTH_STATE_TTL_SECONDS,
        }
    )
    return state, code_challenge


def consume_oauth_state(state: str) -> dict[str, Any] | None:
    """Validate and single-use-consume an OAuth ``state``.

    Reads the ``OAUTH_STATE#{state}`` item, deletes it (so a state is never replayable), and
    returns its payload only when present and unexpired.

    Args:
        state: The ``state`` echoed back by Yahoo on the callback.

    Returns:
        ``{"clerk_user_id", "league_id", "code_verifier"}`` on success, or ``None`` when the
        state is missing, expired, or already consumed.
    """
    if not state:
        return None
    key = {"PK": f"OAUTH_STATE#{state}", "SK": "YAHOO"}
    try:
        response = main.table.get_item(Key=key)
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to read OAuth state: %s", e)
        return None
    item = response.get("Item")
    if not item:
        return None
    # Best-effort single-use delete; the TTL reaps it regardless.
    try:
        main.table.delete_item(Key=key)
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to delete consumed OAuth state: %s", e)
    if int(item.get("expires_at", 0)) < int(time.time()):
        return None
    return {
        "clerk_user_id": item.get("clerk_user_id"),
        "league_id": item.get("league_id", ""),
        "code_verifier": item.get("code_verifier", ""),
    }


def build_authorize_url(state: str, code_challenge: str) -> str:
    """Build the Yahoo consent URL for the given ``state`` and PKCE ``code_challenge``.

    Uses the client id from SSM, the registered ``redirect_uri``, ``response_type=code``, and
    the PKCE ``code_challenge`` (``code_challenge_method=S256``) Yahoo requires.
    """
    params = {
        "client_id": _client_id(),
        "redirect_uri": main.YAHOO_REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{YAHOO_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, code_verifier: str) -> dict[str, Any]:
    """Exchange an authorization ``code`` for Yahoo access + refresh tokens.

    POSTs ``grant_type=authorization_code`` to ``/get_token`` as a PKCE public client:
    ``client_id`` in the body, the matching ``redirect_uri`` and PKCE ``code_verifier``, and
    no client_secret (Yahoo rejects a secret alongside PKCE).

    Raises:
        requests.HTTPError / RequestException: on a Yahoo 4xx/5xx or network failure.
    """
    response = main.http_requests.post(
        YAHOO_TOKEN_URL,
        data={
            "client_id": _client_id(),
            "grant_type": "authorization_code",
            "redirect_uri": main.YAHOO_REDIRECT_URI,
            "code": code,
            "code_verifier": code_verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if not response.ok:
        # An error response carries {"error", "error_description"} (no tokens), so logging it
        # is safe and makes redirect_uri / client_secret / PKCE failures diagnosable. A
        # *successful* body holds tokens and is never logged.
        logger.error(
            "Yahoo token exchange rejected: status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
    response.raise_for_status()
    return response.json()


# The following delegate to the shared token engine (common/yahoo_tokens.py). They are kept
# as module-level names so this module's public surface (and its callers/tests) is unchanged;
# each builds the engine from ``main.*`` at call time via ``_token_client()``.


def refresh_tokens(refresh_token: str) -> dict[str, Any]:
    """Mint a fresh access token from a stored ``refresh_token`` (see YahooTokenClient)."""
    return _token_client().refresh_tokens(refresh_token)


def _encrypt(plaintext: str) -> str:
    """KMS-encrypt a token value, returning base64 ciphertext for DynamoDB storage."""
    return _token_client().encrypt(plaintext)


def _decrypt(ciphertext_b64: str) -> str:
    """KMS-decrypt base64 ciphertext back to the plaintext token value."""
    return _token_client().decrypt(ciphertext_b64)


def store_tokens(clerk_user_id: str, token_response: dict[str, Any]) -> None:
    """Persist an encrypted per-user ``YAHOO_OAUTH`` token item (see YahooTokenClient)."""
    _token_client().store_tokens(clerk_user_id, token_response)


def _get_token_item(clerk_user_id: str) -> dict[str, Any] | None:
    """Read the raw (still-encrypted) ``YAHOO_OAUTH`` item for a user, or ``None``."""
    return _token_client().get_token_item(clerk_user_id)


def has_valid_link(clerk_user_id: str) -> bool:
    """Return whether the caller has a stored Yahoo link (the onboarding gate)."""
    return _token_client().has_valid_link(clerk_user_id)


def get_valid_access_token(clerk_user_id: str) -> str:
    """Return a currently-valid Yahoo access token for the caller, refreshing if needed.

    Raises:
        YahooReauthRequired: when no link exists or the refresh token was revoked.
    """
    return _token_client().get_valid_access_token(clerk_user_id)
