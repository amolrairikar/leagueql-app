## MODIFIED Requirements

### Requirement: Obtain and refresh Yahoo credentials in the onboarder
The onboarder SHALL obtain a valid Yahoo access token for the onboarding owner's linked account
and refresh it as needed for the duration of a run (which can exceed the access token's lifetime),
and SHALL never write Yahoo access/refresh tokens to logs, DynamoDB view items, or S3 raw payloads.
Within a run it SHALL decrypt the owner's access token once and reuse it across its Yahoo requests,
including concurrent ones, re-resolving it only near expiry or after a `401`.
When the owner's Yahoo link is missing or its refresh token has been revoked, onboarding SHALL fail
with a `YAHOO_AUTH` re-link signal rather than a generic failure.

#### Scenario: Token refreshed mid-run
- **WHEN** the onboarder's Yahoo access token nears or reaches expiry during a multi-season fetch
- **THEN** it is transparently refreshed and the run continues without failing

#### Scenario: Revoked Yahoo link
- **WHEN** the onboarding owner's Yahoo refresh token has been revoked
- **THEN** the `JOB_STATUS` item is set to `FAILED` with a `YAHOO_AUTH` code the frontend surfaces
  as a reconnect prompt

#### Scenario: Tokens never persisted
- **WHEN** a Yahoo league is onboarded
- **THEN** no Yahoo access or refresh token value appears in any log line, DynamoDB item, or S3
  object

#### Scenario: One token resolution for the fan-out
- **WHEN** the onboarder fetches a Yahoo league's settings, standings, teams, draft, transactions, game weeks, and every weekly scoreboard concurrently
- **THEN** the owner's stored token is read and decrypted once for the whole fetch, not once per request

#### Scenario: Rejected token on one request
- **WHEN** one of those requests receives a `401`
- **THEN** the onboarder re-resolves the token once and retries that request a single time, and other in-flight requests do not each trigger their own re-resolution
