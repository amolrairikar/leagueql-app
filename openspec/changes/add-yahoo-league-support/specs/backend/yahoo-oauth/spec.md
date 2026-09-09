## Purpose
Add Yahoo Fantasy Sports as a third onboarding platform, which requires OAuth 2.0. This capability covers the authorization-code handshake, the server-side code→token exchange, encrypted token persistence keyed per Clerk user, and automatic access-token refresh — guaranteeing a valid Yahoo access token is available to the onboarder's Yahoo client. The client secret never leaves the backend. This increment ships the account-linking handshake only; the Yahoo Fantasy data client (actual league onboarding) is a later increment.

## ADDED Requirements

### Requirement: Start the authorization flow
`GET /leagues/yahoo/oauth/authorize` (Clerk-authenticated) SHALL return a Yahoo consent URL carrying the OAuth parameters and bind a single-use `state` to the caller, carrying the pending league id so the flow can resume after the callback.

#### Scenario: Authorize URL
- **WHEN** an authenticated caller hits `GET /leagues/yahoo/oauth/authorize` with a `leagueId`
- **THEN** it returns a `.../oauth2/request_auth` URL carrying `client_id`, the registered `redirect_uri`, `response_type=code`, and a single-use `state` bound to the caller (and to the pending `leagueId`), persisted server-side with a short TTL

#### Scenario: Unauthenticated caller
- **WHEN** an unauthenticated caller hits the authorize endpoint
- **THEN** it returns `401`

### Requirement: Handle the OAuth callback
`GET /leagues/yahoo/oauth/callback` (public — Yahoo redirects the browser here with no Clerk JWT) SHALL validate `state`, exchange the code for tokens using Basic auth, persist an encrypted token item, and redirect to the fixed frontend `/connect_league` path.

#### Scenario: Successful callback
- **WHEN** Yahoo redirects to the callback with a valid `state` and `code`
- **THEN** the backend validates and consumes the single-use `state`, `POST`s `.../oauth2/get_token` with `grant_type=authorization_code`, the matching `redirect_uri`, and an `Authorization: Basic base64(client_id:client_secret)` header, persists an encrypted `YAHOO_OAUTH` item keyed to the caller, and `302`-redirects to `/connect_league?platform=YAHOO&yahooLinked=1` carrying the pending `leagueId`

#### Scenario: Invalid state
- **WHEN** `state` is missing, expired, already consumed, or mismatched
- **THEN** the callback `302`-redirects to `/connect_league?platform=YAHOO&yahooLinked=0` and exchanges no code

#### Scenario: User denies or exchange fails
- **WHEN** Yahoo returns `error=access_denied`, or the code exchange fails (invalid code, Yahoo 4xx/5xx, network)
- **THEN** the callback `302`-redirects to `/connect_league?platform=YAHOO&yahooLinked=0`, writing no partial token item, never reflecting an external redirect target

### Requirement: Refresh access tokens transparently
The refresh path SHALL mint a fresh access token from the stored refresh token on an expiry skew, and surface a re-link failure when the refresh token is revoked.

#### Scenario: Expired access token
- **WHEN** an operation needs a Yahoo access token that is expired or within its expiry skew (against the 1-hour lifetime)
- **THEN** a fresh access token is minted via `grant_type=refresh_token` before the data call, not only on a `401`

#### Scenario: Revoked refresh token
- **WHEN** the stored refresh token yields a Yahoo `invalid_grant`
- **THEN** the operation fails with a `YAHOO_AUTH` code the onboarding/refresh flows report to the frontend as a re-link prompt

### Requirement: Protect tokens and secrets
Access/refresh tokens SHALL be encrypted at rest (KMS) and never logged, and `client_id`/`client_secret` SHALL be read from SecureString SSM parameters, never present in env vars/Terraform state/CI.

#### Scenario: Tokens encrypted
- **WHEN** tokens are persisted
- **THEN** access/refresh tokens are encrypted at rest (KMS) and never appear in logs, traces, API responses, or Terraform state

#### Scenario: Secrets from SSM
- **WHEN** the callback/refresh needs the Yahoo credentials
- **THEN** `client_id`/`client_secret` are read from SecureString SSM parameters via `src/common/secrets.py`, absent from Lambda env vars

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
