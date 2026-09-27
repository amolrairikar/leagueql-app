# backend/yahoo-oauth Specification

## Purpose
Add Yahoo Fantasy Sports as a third onboarding platform, which requires OAuth 2.0. This capability covers the authorization-code handshake, the server-side code→token exchange, encrypted token persistence keyed per Clerk user, and automatic access-token refresh — guaranteeing a valid Yahoo access token is available to the onboarder's Yahoo client. The client secret never leaves the backend. This increment ships the account-linking handshake only; the Yahoo Fantasy data client (actual league onboarding) is a later increment.

## Requirements

### Requirement: Start the authorization flow
`GET /leagues/yahoo/oauth/authorize` (Clerk-authenticated) SHALL return a Yahoo consent URL carrying the OAuth + PKCE parameters and bind a single-use `state` to the caller, carrying the pending league id, a return-context `flow`, and a `display` mode (`page` or `popup`) so the callback can resume on the correct frontend page and choose how to hand the result back.

#### Scenario: Authorize URL
- **WHEN** an authenticated caller hits `GET /leagues/yahoo/oauth/authorize` with a `leagueId`
- **THEN** it returns a `.../oauth2/request_auth` URL carrying `client_id`, the registered `redirect_uri`, `response_type=code`, a PKCE `code_challenge` with `code_challenge_method=S256` (Yahoo requires PKCE), and a single-use `state` bound to the caller (and to the pending `leagueId`), with the PKCE `code_verifier` persisted server-side with a short TTL

#### Scenario: Return-context flow carried
- **WHEN** the caller supplies `flow=MIGRATE` (or omits it)
- **THEN** the single-use `state` records the return context (`MIGRATE`, defaulting to `ONBOARD` when omitted) so the callback can choose the return page

#### Scenario: Display mode carried
- **WHEN** the caller supplies `display=popup` (or omits it)
- **THEN** the single-use `state` records the display mode (`popup`, defaulting to `page` when omitted) so the callback returns a `postMessage` page for `popup` and a `302` redirect for `page`

#### Scenario: Unauthenticated caller
- **WHEN** an unauthenticated caller hits the authorize endpoint
- **THEN** it returns `401`

### Requirement: Handle the OAuth callback
`GET /leagues/yahoo/oauth/callback` (public — Yahoo redirects the browser here with no Clerk JWT) SHALL validate `state`, exchange the code for tokens as a PKCE public client (no client_secret), persist an encrypted token item, and hand the result back to the frontend by the mode selected by the state's `display`: for `page` a `302` redirect to the frontend page selected by the return-context `flow` (`/migrate_league` for `MIGRATE`, the landing page `/` otherwise), and for `popup` an HTML page that `postMessage`s the linked/declined result to the opener and closes. A missing/invalid state (no recoverable `display`) SHALL fall back to the `page` redirect.

#### Scenario: Successful callback
- **WHEN** Yahoo redirects to the callback with a valid `state` and `code`
- **THEN** the backend validates and consumes the single-use `state`, `POST`s `.../oauth2/get_token` with `grant_type=authorization_code`, `client_id`, the matching `redirect_uri`, and the stored PKCE `code_verifier` (no client_secret — Yahoo rejects a secret alongside PKCE), and persists an encrypted `YAHOO_OAUTH` item keyed to the caller

#### Scenario: Onboard flow page return
- **WHEN** the consumed `state` records `flow=ONBOARD` (or omits it) and `display=page`
- **THEN** the callback `302`-redirects to the landing page `/?platform=YAHOO&yahooLinked=1&leagueId=<id>` rather than `/connect_league`

#### Scenario: Migrate flow return
- **WHEN** the consumed `state` records `flow=MIGRATE`
- **THEN** the callback `302`-redirects to `/migrate_league?platform=YAHOO&yahooLinked=1&leagueId=<id>` rather than the landing page

#### Scenario: Popup return posts the result to the opener
- **WHEN** the consumed `state` records `display=popup`
- **THEN** the callback responds with an HTML page whose inline script `postMessage`s `{ source: "yahoo-oauth", platform: "YAHOO", yahooLinked, leagueId }` to the opener at the frontend's exact origin and then closes the window, and whose response carries a Content-Security-Policy that permits only that nonce-tagged inline script

#### Scenario: Popup opened without an opener self-redirects
- **WHEN** a `display=popup` callback page runs with no usable `window.opener` (the consent was opened in the same tab because the popup was blocked)
- **THEN** its script instead navigates the current tab to the `page`-mode return URL (`/?platform=YAHOO&yahooLinked=…&leagueId=…`) so onboarding still resumes inline

#### Scenario: Invalid state
- **WHEN** `state` is missing, expired, already consumed, or mismatched
- **THEN** the callback `302`-redirects to the landing page `/?platform=YAHOO&yahooLinked=0` and exchanges no code

#### Scenario: User denies or exchange fails
- **WHEN** Yahoo returns `error=access_denied`, or the code exchange fails (invalid code, Yahoo 4xx/5xx, network)
- **THEN** the callback consumes the echoed `state` to recover its return-context `flow` and `display`, hands back a not-linked (`yahooLinked=0`) result in that mode (a `302` for `page`, a `postMessage` page for `popup`; falling back to the landing page `/` when no usable `state` is present), writing no partial token item and never reflecting an external redirect target

### Requirement: Refresh access tokens transparently
The refresh path SHALL mint a fresh access token from the stored refresh token on an expiry skew, and surface a re-link failure when the refresh token is revoked.

#### Scenario: Expired access token
- **WHEN** an operation needs a Yahoo access token that is expired or within its expiry skew (against the 1-hour lifetime)
- **THEN** a fresh access token is minted via `grant_type=refresh_token` before the data call, not only on a `401`

#### Scenario: Revoked refresh token
- **WHEN** the stored refresh token yields a Yahoo `invalid_grant`
- **THEN** the operation fails with a `YAHOO_AUTH` code the onboarding/refresh flows report to the frontend as a re-link prompt

### Requirement: Protect tokens and secrets
Access/refresh tokens SHALL be encrypted at rest (KMS) and never logged, and the `client_id` SHALL be read from a SecureString SSM parameter, never present in env vars/Terraform state/CI. The app is a PKCE public client, so no client_secret is stored or sent.

#### Scenario: Tokens encrypted
- **WHEN** tokens are persisted
- **THEN** access/refresh tokens are encrypted at rest (KMS) and never appear in logs, traces, API responses, or Terraform state

#### Scenario: Secrets from SSM
- **WHEN** the callback/refresh needs the Yahoo credentials
- **THEN** the `client_id` is read from a SecureString SSM parameter via `src/common/secrets.py`, absent from Lambda env vars (no client_secret exists — PKCE public client)

### Requirement: Require a linked account before Yahoo onboarding
`POST /leagues` for `YAHOO` without a valid linked token SHALL return a "link Yahoo first" signal, and the `Platform` enum SHALL accept `YAHOO` case-insensitively. Yahoo reads are member-gated like ESPN.

#### Scenario: Onboard without a link
- **WHEN** `POST /leagues` for `YAHOO` is called by a caller with no valid `YAHOO_OAUTH` item
- **THEN** it returns a `YAHOO_AUTH` "link Yahoo first" signal the frontend can route on, rather than a generic failure

#### Scenario: Platform enum
- **WHEN** `YAHOO` is supplied wherever `ESPN`/`SLEEPER` are accepted
- **THEN** it is accepted case-insensitively

#### Scenario: Onboard while linked (data client not yet shipped)
- **WHEN** `POST /leagues` for `YAHOO` is called by a caller with a valid linked token
- **THEN** it returns a neutral "Yahoo onboarding is coming soon" signal (the account is linked; the Yahoo Fantasy data client is a later increment), not an error

### Requirement: Delete stored tokens when no longer needed
The token engine SHALL support deleting a user's stored `YAHOO_OAUTH` token item, and this deletion SHALL be idempotent (deleting when no item exists is a no-op). The stored tokens SHALL be removed once the user no longer owns any Yahoo league, so no encrypted credentials are retained beyond their use.

#### Scenario: Delete token item
- **WHEN** `delete_tokens` is called for a user
- **THEN** the `YAHOO_OAUTH` item at `PK=USER#{clerk_user_id}, SK=YAHOO_OAUTH` is removed

#### Scenario: Delete is idempotent
- **WHEN** `delete_tokens` is called for a user with no stored token item
- **THEN** the call succeeds without error and no item is affected
