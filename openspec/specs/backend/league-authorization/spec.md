# league-authorization Specification

## Purpose
Bind each league to an owner and gate state-changing endpoints to that owner, and gate reads of ESPN leagues to verified members. This closes the object-level authorization gap where any valid Clerk JWT could act on any league ID. The owner is the Clerk user who first onboards a league; ESPN membership is verified via the caller's own ESPN cookies; ownership can be transferred with a one-time token.

## Requirements

### Requirement: Owner-gated mutations
State-changing endpoints SHALL be restricted to the league owner, returning `403` for non-owners.

#### Scenario: Owner-gated endpoints
- **WHEN** a non-owner calls `delete`, `migrate`, `refresh`, `espn_members`, or `transfer-token`
- **THEN** the API returns `403`, and the owner's calls succeed

#### Scenario: No owner recorded
- **WHEN** a league was onboarded system-initiated (e.g. Sleeper auto-refresh) so no owner is recorded
- **THEN** owner-gated endpoints raise `403` and recovery is manual

### Requirement: Member-gated ESPN reads
ESPN metadata and query reads SHALL be gated to members via `require_league_member`; Sleeper reads SHALL stay open to any authenticated caller.

#### Scenario: Non-member ESPN read
- **WHEN** a non-member calls `GET /leagues/{id}` or `GET /leagues/{id}/query` for an ESPN league
- **THEN** the API returns `403` (metadata hidden), while the owner/members get `200`

#### Scenario: Sleeper reads open
- **WHEN** any authenticated caller reads a Sleeper league
- **THEN** the read is allowed (existence is not hidden; the gate is a no-op for Sleeper)

### Requirement: Expose owner flag
`GET /leagues/{id}` SHALL return `is_owner` so the frontend can gate owner-only affordances.

#### Scenario: Owner flag
- **WHEN** the owner reads league metadata
- **THEN** `is_owner` is true; for any other caller it is false

### Requirement: Verify ESPN membership
`POST /leagues/{id}/verify-membership` SHALL add the caller to `members` when an authenticated ESPN read with their cookies succeeds, and reject other cases.

#### Scenario: Successful verification
- **WHEN** the caller submits ESPN cookies that ESPN accepts for that exact league
- **THEN** the caller's Clerk user ID is added to `members` (idempotent)

#### Scenario: Rejected cookies
- **WHEN** ESPN rejects the submitted cookies
- **THEN** the API returns `403`

#### Scenario: Non-ESPN or upstream error
- **WHEN** verify-membership is called for a Sleeper league
- **THEN** the API returns `400`; on an ESPN/network error it returns `502`

#### Scenario: Season not taken from client
- **WHEN** verify-membership builds the upstream ESPN read
- **THEN** the season is derived from the league's latest onboarded season, never from client input

### Requirement: Transfer ownership by one-time token
`POST /leagues/{id}/transfer-token` (owner) SHALL mint a single-use token storing only its sha256 hash and a 24h expiry, and `POST /leagues/{id}/claim-ownership` SHALL redeem it via a race-safe conditional write.

#### Scenario: Mint transfer token
- **WHEN** the owner calls `transfer-token`
- **THEN** the API returns a one-time plaintext token and stores only its sha256 hash and expiry

#### Scenario: Claim ownership succeeds
- **WHEN** an authenticated caller redeems a valid, unexpired token
- **THEN** `owner_user_id` is swapped to the caller, they are added to `members`, and the token hash + expiry are removed (single use)

#### Scenario: Claim ownership errors
- **WHEN** claim-ownership is called with no outstanding token/league, a mismatched token, an expired/unparseable expiry, or an already-redeemed token
- **THEN** the API returns `404`, `403`, `410`, or `409` respectively

#### Scenario: After handoff
- **WHEN** ownership has been transferred
- **THEN** the new owner can mutate the league and the previous owner gets `403`

### Requirement: Job status stays unauthenticated
`GET /jobs/{jobId}` SHALL remain unauthenticated.

#### Scenario: Job-status polling
- **WHEN** the frontend polls `get_job`
- **THEN** the request succeeds without authentication
