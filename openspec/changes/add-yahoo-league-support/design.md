## Context

Yahoo Fantasy is the third onboarding platform. Unlike ESPN (per-request cookies) and
Sleeper (public API), Yahoo requires an OAuth 2.0 authorization-code handshake. The two
capability specs (`backend/yahoo-oauth`, `frontend/connect-yahoo-league`) were authored
during the initial OpenSpec migration and relocated here as a pending change. Yahoo is now
committed, so this change implements the **account-linking increment**.

## Goals / Non-Goals

- **Goal:** ship the OAuth link round-trip end-to-end: authorize → Yahoo consent →
  callback → encrypted per-user token persistence → transparent refresh.
- **Goal:** wire the frontend Connect flow so selecting Yahoo + a league id + Connect starts
  the OAuth redirect and resumes on return.
- **Non-Goal (this increment):** the Yahoo Fantasy **data client** (fetching leagues/teams/
  matchups/draft/transactions and transforming them). A linked Yahoo onboard surfaces a
  neutral "coming soon" signal until that lands.

## Decisions

- **Authorization-code flow with PKCE (S256) + client_secret Basic auth.** Yahoo **requires
  PKCE** on the authorize request — without a `code_challenge` it rejects the request with
  `invalid_request: invalid code challenge or method`. So authorize sends a `code_challenge`
  (`code_challenge_method=S256`) and the token exchange sends the matching `code_verifier`,
  alongside the `Authorization: Basic base64(client_id:client_secret)` header (a confidential
  client may combine both). The `code_verifier` is stored server-side with the OAuth state and
  never reaches the browser. (An earlier iteration dropped PKCE based on Yahoo's docs, but the
  live API rejected it.) `scope` is left at the app default configured on the Yahoo app.
- **Two new routes on the existing API Lambda.** `GET /leagues/yahoo/oauth/authorize` (Clerk-authed)
  and `GET /leagues/yahoo/oauth/callback` (**public** — Yahoo redirects the browser here with no Clerk
  JWT, like `/health`). Declared in `docs/api/openapi_spec.yaml`; the callback omits the
  `security:` block.
- **Single-use `state` in DynamoDB with TTL.** Authorize mints a random `state`, stores
  `PK=OAUTH_STATE#{state}, SK=YAHOO` with the caller's Clerk user id, the pending `leagueId`,
  the PKCE `code_verifier`, and a `ttl` (~10 min). Callback consumes (get + delete) and
  validates it, using the stored `code_verifier` for the token exchange. This survives the
  stateless authorize→callback redirect across Lambda invocations.
- **Encrypted per-user token item.** `PK=USER#{clerk_user_id}, SK=YAHOO_OAUTH` holds the
  KMS-encrypted access + refresh tokens (base64 ciphertext), `expires_at` (epoch), and
  `token_type`. A dedicated KMS key encrypts/decrypts; plaintext tokens never touch logs,
  traces, API responses, or Terraform state.
- **Transparent refresh with skew.** `get_valid_access_token` refreshes via
  `grant_type=refresh_token` when within the expiry skew, persisting any rotated refresh
  token. A Yahoo `invalid_grant` raises a `YAHOO_AUTH` re-link signal.
- **Onboarding gate.** `POST /leagues` for `YAHOO` checks for a valid linked token: unlinked
  → `YAHOO_AUTH` "link Yahoo first" signal; linked → neutral "coming soon" signal (no
  onboarder invocation this increment). `Platform` enum gains `YAHOO` (case-insensitive).
- **Secrets from SSM.** `client_id`/`client_secret` read from SecureString SSM parameters
  (`/leagueql/{env}/yahoo/client_id`, `/leagueql/{env}/yahoo/client_secret`) via
  `common/secrets.py`; only the parameter *names* are in env vars.
- **Frontend.** Landing-page Connect for Yahoo calls authorize and full-page-redirects. The
  `/connect_league` page is the fixed return target: `yahooLinked=1` → "connected" +
  resume onboard (shows the "coming soon" notice); `yahooLinked=0` → inline retry alert.
  Disabled in demo mode.

## Risks / Trade-offs

- **PKCE state storage:** the `code_verifier` must survive the authorize→callback redirect, so
  it lives in the `OAUTH_STATE` item (short TTL, single-use) rather than a cookie/session.
- **"Coming soon" onboard:** the linked-but-unonboardable state is intentional for this
  increment; the frontend renders it as a neutral notice, not a failure.

## Open Questions

- Yahoo Fantasy data client shape (endpoints, rate limits, transforms) — deferred to the next
  increment.
