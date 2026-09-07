# league-authorization Specification

## Purpose
Bind each league to an owner and gate state-changing endpoints to that owner, and gate reads of ESPN leagues to verified members. This closes the object-level authorization gap where any valid Clerk JWT could act on any league ID. The owner is the Clerk user who first onboards a league; ESPN membership is granted by redeeming an owner-shared invite link; ownership can be transferred with a one-time token.

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

### Requirement: Mint an ESPN invite token
`POST /leagues/{id}/invite-token` (owner-gated) SHALL mint a reusable invite token for an ESPN league, storing only its sha256 hash on METADATA and returning the plaintext token once. Minting again SHALL overwrite the stored hash, invalidating any previously shared link.

#### Scenario: Owner mints an invite token
- **WHEN** the league owner calls `invite-token` for an ESPN league
- **THEN** the API returns a plaintext token once and stores only its sha256 hash (`invite_token_hash`) on METADATA, with no expiry

#### Scenario: Non-owner mint rejected
- **WHEN** a non-owner (or a caller for a league with no recorded owner) calls `invite-token`
- **THEN** the API returns `403`

#### Scenario: Regenerating invalidates the old link
- **WHEN** the owner mints a new invite token while one is already outstanding
- **THEN** the stored hash is overwritten so the previously shared token no longer redeems

#### Scenario: Non-ESPN rejected
- **WHEN** `invite-token` is called for a Sleeper league
- **THEN** the API returns `400` (Sleeper reads are open, so no invite is needed)

### Requirement: Redeem an ESPN invite token
`POST /leagues/{id}/accept-invite` SHALL add the authenticated caller to `members` when the submitted token matches the stored hash, without requiring any ESPN cookies. The token SHALL be reusable (the stored hash is not consumed on redemption).

#### Scenario: Successful redemption
- **WHEN** an authenticated caller submits a token whose sha256 hash matches the league's stored `invite_token_hash`
- **THEN** the caller's Clerk user ID is added to `members` (idempotent), the stored hash is left intact so other leaguemates can still redeem it, and the API returns `200`

#### Scenario: Reusable across leaguemates
- **WHEN** a second authenticated caller redeems the same still-outstanding token
- **THEN** that caller is also added to `members` and the API returns `200`

#### Scenario: No outstanding token
- **WHEN** `accept-invite` is called for a league that has no stored `invite_token_hash`
- **THEN** the API returns `404`

#### Scenario: Token mismatch
- **WHEN** the submitted token does not match the stored hash (compared in constant time)
- **THEN** the API returns `403`

#### Scenario: Non-ESPN rejected
- **WHEN** `accept-invite` is called for a Sleeper league
- **THEN** the API returns `400`

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
