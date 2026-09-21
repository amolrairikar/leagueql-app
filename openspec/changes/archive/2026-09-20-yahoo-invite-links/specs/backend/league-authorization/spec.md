## REMOVED Requirements

### Requirement: Mint an ESPN invite token
**Reason**: Generalized to all gated platforms (ESPN and Yahoo); replaced by the platform-neutral "Mint an invite token".
**Migration**: Behavior and endpoint are unchanged for ESPN; the guard now also accepts Yahoo and rejects only Sleeper. See ADDED "Mint an invite token".

### Requirement: Redeem an ESPN invite token
**Reason**: Generalized to all gated platforms (ESPN and Yahoo); replaced by the platform-neutral "Redeem an invite token".
**Migration**: Behavior and endpoint are unchanged for ESPN; redemption now also works for Yahoo and rejects only Sleeper. See ADDED "Redeem an invite token".

## ADDED Requirements

### Requirement: Mint an invite token
`POST /leagues/{id}/invite-token` (owner-gated) SHALL mint a reusable invite token for a gated league (ESPN or Yahoo), storing only its sha256 hash on METADATA and returning the plaintext token once. Minting again SHALL overwrite the stored hash, invalidating any previously shared link. Sleeper leagues (whose reads are open) SHALL be rejected with `400`.

#### Scenario: Owner mints an invite token
- **WHEN** the league owner calls `invite-token` for an ESPN or Yahoo league
- **THEN** the API returns a plaintext token once and stores only its sha256 hash (`invite_token_hash`) on METADATA, with no expiry

#### Scenario: Non-owner mint rejected
- **WHEN** a non-owner (or a caller for a league with no recorded owner) calls `invite-token`
- **THEN** the API returns `403`

#### Scenario: Regenerating invalidates the old link
- **WHEN** the owner mints a new invite token while one is already outstanding
- **THEN** the stored hash is overwritten so the previously shared token no longer redeems

#### Scenario: Sleeper rejected
- **WHEN** `invite-token` is called for a Sleeper league
- **THEN** the API returns `400` (Sleeper reads are open, so no invite is needed)

### Requirement: Redeem an invite token
`POST /leagues/{id}/accept-invite` SHALL add the authenticated caller to `members` when the submitted token matches the stored hash, without requiring any platform credentials of their own, for a gated league (ESPN or Yahoo). The token SHALL be reusable (the stored hash is not consumed on redemption). Sleeper leagues SHALL be rejected with `400`.

#### Scenario: Successful redemption
- **WHEN** an authenticated caller submits a token whose sha256 hash matches an ESPN or Yahoo league's stored `invite_token_hash`
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

#### Scenario: Sleeper rejected
- **WHEN** `accept-invite` is called for a Sleeper league
- **THEN** the API returns `400`
