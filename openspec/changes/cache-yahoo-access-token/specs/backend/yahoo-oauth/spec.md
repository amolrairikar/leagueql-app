## MODIFIED Requirements

### Requirement: Refresh access tokens transparently
The refresh path SHALL mint a fresh access token from the stored refresh token on an expiry skew, and surface a re-link failure when the refresh token is revoked. A long-running operation that makes many Yahoo calls with one owner's token SHALL decrypt that token once and reuse it until it is within its expiry skew, rather than decrypting it again for every call.

#### Scenario: Expired access token
- **WHEN** an operation needs a Yahoo access token that is expired or within its expiry skew (against the 1-hour lifetime)
- **THEN** a fresh access token is minted via `grant_type=refresh_token` before the data call, not only on a `401`

#### Scenario: Revoked refresh token
- **WHEN** the stored refresh token yields a Yahoo `invalid_grant`
- **THEN** the operation fails with a `YAHOO_AUTH` code the onboarding/refresh flows report to the frontend as a re-link prompt

#### Scenario: Token reused across many calls
- **WHEN** one operation sends many Yahoo requests while the access token is outside its expiry skew
- **THEN** the stored token is read and decrypted once for the whole span, and every request uses that same access token

#### Scenario: Token re-resolved near expiry
- **WHEN** the reused access token comes within its expiry skew during a long operation
- **THEN** the next request resolves a valid token again (refreshing it if needed) and later requests reuse that new token

#### Scenario: Token rejected by Yahoo
- **WHEN** Yahoo answers a request with `401` while the operation holds a reused token
- **THEN** the operation discards the reused token and re-resolves it from the stored item before the single retry, instead of resending the rejected token

#### Scenario: Concurrent callers share one resolution
- **WHEN** several concurrent requests of one operation need the token at the same moment (at start or after expiry or a `401`)
- **THEN** the token is resolved once and all of them use the result, not one decrypt or refresh per request

#### Scenario: Reuse never leaks the token
- **WHEN** a token is reused across requests
- **THEN** it is held only in the running operation's memory and never appears in logs, traces, API responses, DynamoDB, or S3

#### Scenario: Tokens never cross users
- **WHEN** two different owners' operations run one after another in the same process
- **THEN** every Yahoo request of each operation carries only that owner's access token, and no token is retained after its operation ends
