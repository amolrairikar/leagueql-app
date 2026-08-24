# yahoo-oauth Specification

## Purpose
Add Yahoo Fantasy Sports as a third onboarding platform, which requires OAuth 2.0. This capability covers the authorization-code handshake (with PKCE), the server-side code→token exchange, encrypted token persistence keyed per Clerk user, and automatic access-token refresh — guaranteeing a valid Yahoo access token is available to the onboarder's Yahoo client. The client secret never leaves the backend.

## Requirements

### Requirement: Start the authorization flow
`GET /auth/yahoo/authorize` (Clerk-authenticated) SHALL return a Yahoo consent URL carrying the OAuth + PKCE parameters and bind a single-use `state` to the caller.

#### Scenario: Authorize URL
- **WHEN** an authenticated caller hits `GET /auth/yahoo/authorize`
- **THEN** it returns a `.../oauth2/request_auth` URL carrying `client_id`, the registered `redirect_uri`, `response_type=code`, `scope=fspt-r`, a single-use `state` bound to the caller, and a PKCE `code_challenge` with `code_challenge_method=S256`, without requesting `openid`/`nonce`

#### Scenario: Unauthenticated caller
- **WHEN** an unauthenticated caller hits the authorize endpoint
- **THEN** it returns `401`

### Requirement: Handle the OAuth callback
`GET /auth/yahoo/callback` SHALL validate `state`, exchange the code for tokens using the stored PKCE verifier and Basic auth, persist an encrypted token item, and redirect to a fixed frontend path.

#### Scenario: Successful callback
- **WHEN** Yahoo redirects to the callback with a valid `state` and `code`
- **THEN** the backend validates `state`, `POST`s `.../oauth2/get_token` with `grant_type=authorization_code`, the matching `redirect_uri`, the stored PKCE `code_verifier`, and an `Authorization: Basic base64(client_id:client_secret)` header, persists an encrypted `YAHOO_OAUTH` item, and `302`-redirects to a fixed frontend path with a linked marker

#### Scenario: Invalid state
- **WHEN** `state` is missing, expired, mismatched, or maps to a different user
- **THEN** the callback returns `400` and exchanges no code

#### Scenario: User denies or exchange fails
- **WHEN** Yahoo returns `access_denied`, or the code exchange fails (invalid code, Yahoo 4xx/5xx, network)
- **THEN** the callback `302`-redirects to the fixed frontend path with a declined/failed marker, writing no partial token item, never reflecting an external redirect target

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
- **THEN** access/refresh tokens are encrypted at rest and never appear in logs, traces, API responses, or Terraform state

#### Scenario: Secrets from SSM
- **WHEN** the callback/refresh needs the Yahoo credentials
- **THEN** `client_id`/`client_secret` are read from SecureString SSM parameters via `src/common/secrets.py`, absent from Lambda env vars

### Requirement: Require a linked account before Yahoo onboarding
`POST /leagues` for `YAHOO` without a valid linked token SHALL return a "link Yahoo first" signal, and the `Platform` enum SHALL accept `YAHOO` case-insensitively. Yahoo reads are member-gated like ESPN.

#### Scenario: Onboard without a link
- **WHEN** `POST /leagues` for `YAHOO` is called by a caller with no valid `YAHOO_OAUTH` item
- **THEN** it returns a "link Yahoo first" signal the frontend can route on, rather than a generic failure

#### Scenario: Platform enum
- **WHEN** `YAHOO` is supplied wherever `ESPN`/`SLEEPER` are accepted
- **THEN** it is accepted case-insensitively, and the first Yahoo ONBOARD records the onboarding Clerk user as owner
