## MODIFIED Requirements

### Requirement: Gate owner-only actions
The sidebar SHALL show Refresh / Migrate / Transfer Ownership / Invite Leaguemates / Delete only when the caller is the owner; non-owners SHALL see View Another League and Claim Ownership, with owner actions hidden until `getLeague` resolves.

#### Scenario: Owner vs non-owner
- **WHEN** the sidebar renders for a league
- **THEN** Refresh, Migrate, Transfer Ownership, Invite Leaguemates, and Delete appear only when `is_owner`, while non-owners see View Another League and Claim Ownership

#### Scenario: Owner state loading and failure
- **WHEN** `getLeague` has not resolved, or fails, or the app is in demo/no-league
- **THEN** owner-only actions stay hidden until it resolves (no flash), a failed request resolves to non-owner, and demo/no-league bypasses gating

## ADDED Requirements

### Requirement: Owner shares an ESPN invite link
An owner SHALL be able to mint a reusable invite link for an ESPN league and copy it to share with leaguemates.

#### Scenario: Create invite link
- **WHEN** the owner opens the Invite Leaguemates dialog and creates a link
- **THEN** a reusable link (containing the league ID, platform, and minted token) is shown and copyable, closing the dialog clears it, and the dialog notes that anyone with the link can view the league and that creating a new link revokes the old one

### Requirement: Redeem an ESPN invite link
A signed-in user who opens an invite link SHALL be added to the league's members and taken to its dashboard, without supplying ESPN cookies.

#### Scenario: Redeem a valid link
- **WHEN** a signed-in user opens the invite link and its token is valid
- **THEN** the user is added to the league's members, the league cookies are set, and they are routed to the dashboard

#### Scenario: Redeem an invalid or revoked link
- **WHEN** the invite token is missing, malformed, or no longer matches the stored hash
- **THEN** an inline error is shown asking the user to request a new link from the league owner, and they are not routed into the league

### Requirement: Non-member ESPN read directs to an invite link
An ESPN league returning `403` for a non-member SHALL show a message directing the caller to obtain an invite link from the league owner, rather than prompting for ESPN cookies.

#### Scenario: Non-member sees invite-link guidance
- **WHEN** `getLeague` returns `403` for an ESPN league
- **THEN** the `MembershipGuard` shows a backdrop explaining the league is private and that the caller needs an invite link from the owner to join, with no cookie-entry form

## REMOVED Requirements

### Requirement: Verify ESPN membership for non-members
**Reason**: Replaced by the invite-link flow; leaguemates no longer submit ESPN cookies to join.
**Migration**: A non-member joins by opening an owner-shared invite link (the `/join/:leagueId` redemption page). The cookie-entry Join League dialog and the frontend `verifyMembership` call are removed.
