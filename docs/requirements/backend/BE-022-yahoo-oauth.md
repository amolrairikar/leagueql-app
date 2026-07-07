# BE-022: Yahoo OAuth Authorization & Token Management

## Description
Adds Yahoo Fantasy Sports as a third onboarding platform (`YAHOO`, alongside `ESPN` and
`SLEEPER`). Yahoo's Fantasy Sports API requires **OAuth 2.0** — unlike Sleeper (public API,
no auth) and ESPN (per-request `s2`/`SWID` cookies, never persisted), Yahoo requires a
signed-in user to grant LeagueQL access to their fantasy data, after which LeagueQL holds a
short-lived access token and a long-lived refresh token on the user's behalf.

This doc covers the **OAuth handshake and token lifecycle** — the authorization-code flow, the
server-side code→token exchange, encrypted token persistence, and automatic access-token
refresh. The Yahoo data fetch during onboarding (a `YahooClient` in the onboarder, analogous to
`espn_client.py` / `sleeper_client.py`) consumes the token minted here and is scoped under
[BE-001](BE-001-league-onboarding.md); this doc only guarantees a valid access token is
available to it.

**Authorization-code flow (server-side, secret never leaves the backend):**
1. **Start.** `GET /auth/yahoo/authorize` (Clerk-authenticated) generates a single-use `state`
   value bound to the caller's Clerk user ID **and a PKCE `code_verifier`**, persists both with
   a short TTL, and returns the Yahoo consent URL
   (`https://api.login.yahoo.com/oauth2/request_auth`) carrying `client_id`, `redirect_uri`,
   `response_type=code`, `scope` (`fspt-r`, read-only Yahoo Fantasy), `state`, and the PKCE
   `code_challenge` + `code_challenge_method=S256`. PKCE is only *strongly recommended* for a
   confidential client (we hold a secret), but we adopt it. We do **not** request `openid` /
   send a `nonce`: that OIDC "Sign in with Yahoo" identity flow is unnecessary because Clerk is
   our identity provider — we only need Fantasy Sports read access, so the app is registered
   with the **Fantasy Sports → Read** API permission.
2. **Consent.** The browser is sent to Yahoo; the user signs in and approves.
3. **Callback.** Yahoo redirects the browser to the registered **redirect URI**
   (`https://api.leagueql.com/auth/yahoo/callback`) with `?code=…&state=…`. The backend
   validates `state` (CSRF + Clerk-user binding), then `POST`s to Yahoo's token endpoint
   (`https://api.login.yahoo.com/oauth2/get_token`) with `grant_type=authorization_code`, the
   `code`, the **same `redirect_uri`**, and the stored PKCE `code_verifier`, authenticating with
   an `Authorization: Basic base64(client_id:client_secret)` header (secret from SSM). It
   receives `access_token` + `refresh_token` + `expires_in`, persists them **encrypted** keyed by
   the Clerk user, and `302`-redirects the browser back to the frontend connect flow
   (`https://leagueql.com/connect_league?platform=YAHOO&yahooLinked=1`).
4. **Use / refresh.** Onboarding, refresh, and any scheduled Yahoo job resolve a valid access
   token via the stored refresh token (`POST get_token` with `grant_type=refresh_token`, same
   Basic-auth header), minting a fresh access token when the current one (1-hour lifetime) is
   within its expiry skew.

**Secrets.** The Yahoo `client_id` and `client_secret` are stored as **SecureString** SSM
parameters (`/leagueql/{env}/yahoo/client_id`, `/leagueql/{env}/yahoo/client_secret`) and read
at cold start via [`src/common/secrets.py`](../../../src/common/secrets.py), following the
Stripe-secret pattern (BE-015) — never in env vars, Terraform state, or CI.

**Redirect URI.** Prod registers `https://api.leagueql.com/auth/yahoo/callback`. Yahoo requires
HTTPS in production (localhost is allowed for local dev, and `oob` exists for browserless apps),
and the callback in the token exchange **must exactly match the registered URI** — Yahoo matches
one registered redirect per app, so **each environment registers its own Yahoo app** with its own
redirect URI.

## Scope
- New endpoints (`src/api/routes.py`): `GET /auth/yahoo/authorize` (Clerk-gated),
  `GET /auth/yahoo/callback` (public — reached by Yahoo's redirect, guarded by `state`).
- `Platform` enum gains `YAHOO` (`src/api/main.py`).
- Token module (new, e.g. `src/common/yahoo_oauth.py`): build authorize URL, exchange code,
  refresh access token, encrypt/decrypt + persist/load tokens.
- Secrets: `get_secret_from_env_param` for `client_id` / `client_secret`
  (`src/common/secrets.py`).
- New DynamoDB item **`YAHOO_OAUTH`** keyed per Clerk user
  (`PK = USER#{clerk_user_id}`, `SK = YAHOO_OAUTH`) storing the **encrypted** refresh token,
  encrypted access token, `expires_at`, and Yahoo GUID — see
  [`dynamodb_spec.md`](../../db/dynamodb_spec.md). Access/refresh tokens are encrypted at rest
  (KMS) and never logged.
- Short-lived **`YAHOO_OAUTH_STATE`** item (or equivalent) with TTL holding the CSRF `state`,
  the initiating Clerk user, and the PKCE `code_verifier` (consumed on callback).
- Consumed by the onboarder's `YahooClient` under [BE-001](BE-001-league-onboarding.md) and by
  Yahoo refresh under [BE-002](BE-002-league-refresh.md).
- Terraform: SSM SecureString params, KMS key/grant, and API Gateway routes for the two
  endpoints.

## Edge Cases
- **`state` mismatch / missing / expired:** callback returns `400` and does not exchange the
  code; the frontend surfaces a "linking failed, try again" state. `state` is single-use and
  bound to the initiating Clerk user — a callback whose `state` maps to a different user is
  rejected.
- **User denies consent:** Yahoo redirects with `?error=access_denied`; the callback
  `302`s back to the frontend with a not-linked/declined marker rather than erroring hard.
- **Code exchange fails (invalid code, Yahoo 4xx/5xx, network):** callback records nothing,
  redirects back with a failure marker; no partial/empty token item is written.
- **Access token expired at use time:** the refresh path mints a new access token from the
  stored refresh token before the Yahoo data call; expiry is checked with a safety skew (e.g.
  refresh when < 5 min remaining) rather than only on a `401`.
- **Refresh token revoked (user unlinked Yahoo or changed permissions):** Yahoo refresh tokens
  are long-lived and survive password changes, but a revoked token makes refresh
  yield a Yahoo `invalid_grant`; the stored token item is marked/removed and the operation
  fails with a friendly `YAHOO_AUTH` code so the frontend can prompt a **re-link**. Onboarding
  and refresh surface this like ESPN's `ESPN_AUTH`.
- **Token never persisted in plaintext or logs:** access/refresh tokens are encrypted at rest
  and redacted from logs/traces, mirroring the ESPN-cookie rule (BE-001).
- **Re-authorizing an already-linked user:** a fresh consent overwrites the stored token item
  (idempotent); a new refresh token replaces the prior one.
- **Yahoo GUID vs. Clerk user:** the token is tied to the **Yahoo** account that consented; the
  item records the Yahoo GUID so a user who links a different Yahoo account replaces the prior
  link. League→user ownership is still governed by Clerk (BE-016), not the Yahoo GUID.
- **Onboarding a Yahoo league without a linked account:** `POST /leagues` for `YAHOO` when the
  caller has no valid `YAHOO_OAUTH` item returns a `409`/`428`-style "link Yahoo first" signal
  rather than a generic failure, so the frontend routes to the link step.
- **Scheduled/system Yahoo refresh:** any future scheduled Yahoo refresh (cf.
  [BE-012](BE-012-scheduled-sleeper-auto-refresh.md)) must run under a stored refresh token; if
  the token is gone it is skipped with a logged `YAHOO_AUTH`, not retried into failure.
- **CSRF/open-redirect hardening:** the callback only ever redirects to a fixed allow-listed
  frontend path; it never reflects an attacker-supplied `redirect`/`next` parameter.

## Acceptance Criteria
- [ ] `GET /auth/yahoo/authorize` (Clerk-authenticated) returns a Yahoo consent URL
      (`.../oauth2/request_auth`) carrying `client_id`, the registered `redirect_uri`,
      `response_type=code`, `scope=fspt-r`, a single-use `state` bound to the caller, and a PKCE
      `code_challenge` (`code_challenge_method=S256`); it does not request `openid`/`nonce`.
      Unauthenticated callers get `401`.
- [ ] `GET /auth/yahoo/callback` validates `state`, `POST`s `.../oauth2/get_token` with
      `grant_type=authorization_code`, the matching `redirect_uri`, the stored PKCE
      `code_verifier`, and an `Authorization: Basic base64(client_id:client_secret)` header
      (secret from SSM), and persists an encrypted `YAHOO_OAUTH` token item for the user.
- [ ] The callback `302`-redirects to a fixed frontend path with a linked marker on success and
      a distinct declined/failed marker on `access_denied` or exchange failure — never reflecting
      an external redirect target.
- [ ] `state` is single-use, TTL-bound, and user-bound; a missing/expired/mismatched/cross-user
      `state` yields `400` with no token exchange.
- [ ] Access/refresh tokens are encrypted at rest (KMS) and never appear in logs, traces, API
      responses, or Terraform state.
- [ ] A caller with an expired access token but a valid refresh token transparently gets a fresh
      access token via `grant_type=refresh_token` (refreshed on an expiry skew against the 1-hour
      access-token lifetime, not only on `401`).
- [ ] A revoked/expired refresh token surfaces a `YAHOO_AUTH` failure that the onboarding/refresh
      flows report to the frontend as a re-link prompt.
- [ ] `POST /leagues` for `YAHOO` with no valid linked token returns a "link Yahoo first" signal
      the frontend can route on, rather than a generic onboarding failure.
- [ ] `client_id` / `client_secret` are read from SecureString SSM parameters via
      `src/common/secrets.py`; neither is present in Lambda env vars.
- [ ] The `Platform` enum accepts `YAHOO` case-insensitively wherever `ESPN`/`SLEEPER` are
      accepted.

## Authorization (BE-016)
The OAuth link is per **Clerk user** and grants no league access on its own. League ownership
and membership are still governed by [BE-016](BE-016-league-ownership-authorization.md): the
first Yahoo ONBOARD records the onboarding Clerk user as owner. Yahoo reads are gated like ESPN
(league data is account-scoped, not public) — treated as member-gated in
`require_league_member` rather than the open Sleeper path.

## Sources
`src/api/routes.py`, `src/api/main.py` (`Platform`), `src/common/yahoo_oauth.py` (new),
`src/common/secrets.py`, `src/onboarder/` (Yahoo client — BE-001),
`docs/db/dynamodb_spec.md` (`YAHOO_OAUTH`), `docs/api/openapi_spec.yaml`, `infrastructure/`.
