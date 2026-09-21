## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Owner shares an ESPN invite link
**Reason**: Generalized to gated platforms (ESPN and Yahoo); replaced by "Owner shares an invite link".
**Migration**: See ADDED "Owner shares an invite link" — same dialog, now available for Yahoo as well as ESPN.

### Requirement: Redeem an ESPN invite link
**Reason**: Generalized to gated platforms (ESPN and Yahoo); replaced by "Redeem an invite link".
**Migration**: See ADDED "Redeem an invite link" — same `/join` page, now redeems Yahoo links too.

### Requirement: Non-member ESPN read directs to an invite link
**Reason**: Generalized to gated platforms (ESPN and Yahoo); replaced by "Non-member read directs to an invite link".
**Migration**: See ADDED "Non-member read directs to an invite link" — the private-league backdrop now covers Yahoo.

## ADDED Requirements

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
