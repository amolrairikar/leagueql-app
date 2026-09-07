## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Verify ESPN membership
**Reason**: Replaced by the owner-shared invite-link flow. Requiring each leaguemate to submit their own ESPN cookies was the friction this change removes; membership now comes from redeeming an owner-minted invite token instead.
**Migration**: Non-owners join a private ESPN league by opening the owner's invite link and redeeming it via `POST /leagues/{id}/accept-invite`. The `POST /leagues/{id}/verify-membership` endpoint is removed. Already-stored `members` sets are unaffected; ownership transfer (`transfer-token`/`claim-ownership`) still adds the new owner to `members`.
