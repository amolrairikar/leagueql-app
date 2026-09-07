## MODIFIED Requirements

### Requirement: Ownership/membership-aware routing
The initial `getLeague` check SHALL route by outcome so a non-owner is not sent through an owner-only refresh, and an ESPN non-member is directed to obtain an invite link rather than being asked for ESPN cookies.

#### Scenario: Non-owner of an existing league
- **WHEN** the league exists (`200`) and the caller is not its owner
- **THEN** the flow opens the dashboard without sending an owner-only refresh

#### Scenario: ESPN non-member join
- **WHEN** the lookup returns `403` for an ESPN league
- **THEN** the flow does not attempt cookie-based membership verification; it surfaces a message that the league is private and the caller needs an invite link from the league owner to join
