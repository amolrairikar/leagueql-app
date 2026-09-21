# ownership-transfer Specification

## Purpose
Surface league ownership in the UI: gate owner-only sidebar actions to the owner, let owners share an invite link and direct non-members to one, and provide the ownership transfer/claim flow. Owner state comes from the current league's `is_owner`, and mutating call sites surface a `403` as an owner-only/membership message inline.

## Requirements

### Requirement: Gate owner-only actions
The sidebar SHALL show Refresh / Migrate / Transfer Ownership / Invite Leaguemates / Delete only when the caller is the owner; non-owners SHALL see View Another League and Claim Ownership, with owner actions hidden until `getLeague` resolves. Invite Leaguemates SHALL appear only for gated platforms (ESPN or Yahoo), not for Sleeper (whose reads are open).

#### Scenario: Owner vs non-owner
- **WHEN** the sidebar renders for a league
- **THEN** Refresh, Migrate, Transfer Ownership, Invite Leaguemates, and Delete appear only when `is_owner`, while non-owners see View Another League and Claim Ownership

#### Scenario: Invite action gated to gated platforms
- **WHEN** the owner views an ESPN or Yahoo league versus a Sleeper league
- **THEN** Invite Leaguemates appears for the ESPN/Yahoo league and is hidden for the Sleeper league

#### Scenario: Owner state loading and failure
- **WHEN** `getLeague` has not resolved, or fails, or the app is in demo/no-league
- **THEN** owner-only actions stay hidden until it resolves (no flash), a failed request resolves to non-owner, and demo/no-league bypasses gating

### Requirement: Owner shares an invite link
An owner SHALL be able to mint a reusable invite link for a gated league (ESPN or Yahoo) and copy it to share with leaguemates.

#### Scenario: Create invite link
- **WHEN** the owner opens the Invite Leaguemates dialog for an ESPN or Yahoo league and creates a link
- **THEN** a reusable link (containing the league ID, platform, and minted token) is shown and copyable, closing the dialog clears it, and the dialog notes that anyone with the link can view the league without their own ESPN or Yahoo login and that creating a new link revokes the old one

### Requirement: Redeem an invite link
A signed-in user who opens an invite link SHALL be added to the league's members and taken to its dashboard, without supplying any platform credentials of their own.

#### Scenario: Redeem a valid link
- **WHEN** a signed-in user opens the invite link for an ESPN or Yahoo league and its token is valid
- **THEN** the user is added to the league's members, the league cookies are set, and they are routed to the dashboard

#### Scenario: Redeem an invalid or revoked link
- **WHEN** the invite token is missing, malformed, the platform is Sleeper, or the token no longer matches the stored hash
- **THEN** an inline error is shown asking the user to request a new link from the league owner, and they are not routed into the league

### Requirement: Non-member read directs to an invite link
A gated league (ESPN or Yahoo) returning `403` for a non-member SHALL show a message directing the caller to obtain an invite link from the league owner, rather than prompting for platform credentials.

#### Scenario: Non-member sees invite-link guidance
- **WHEN** `getLeague` returns `403` for an ESPN or Yahoo league
- **THEN** the `MembershipGuard` shows a backdrop explaining the league is private and that the caller needs an invite link from the owner to join, with no cookie-entry form

### Requirement: Transfer and claim ownership
An owner SHALL be able to mint a one-time transfer token, and a recipient SHALL be able to redeem it, reloading league state on success.

#### Scenario: Mint token
- **WHEN** the owner opens the Transfer Ownership dialog
- **THEN** a one-time token is minted and copyable, and closing the dialog clears it

#### Scenario: Claim ownership
- **WHEN** a recipient redeems a valid token via the Claim Ownership dialog
- **THEN** the API cache is cleared and league state reloads so the new owner immediately sees owner actions

### Requirement: Inline 403 messaging
A `403` on a mutating endpoint SHALL render a clear owner-only message inline (via `toResult` + `<ErrorAlert>`), with no global error banner.

#### Scenario: Owner-only 403
- **WHEN** a mutating call returns `403`
- **THEN** an inline owner-only/membership message is shown rather than a generic error
