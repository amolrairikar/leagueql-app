## MODIFIED Requirements

### Requirement: Document ownership & access
`/docs` SHALL include an Ownership & Access section covering the owner model, joining a private ESPN league via membership verification, and one-time-token ownership transfer, and its owner-actions list SHALL mark the actions that are available only for ESPN leagues (Refresh League, Invite Leaguemates) as ESPN only.

#### Scenario: Ownership instructions
- **WHEN** the Ownership & Access section renders
- **THEN** it documents the first-connector-is-owner model, that owner-only actions are hidden from non-owners, how a non-owner joins a private ESPN league via membership verification (with the "Join league" dialog screenshot), and the one-time-token ownership transfer/claim flow

#### Scenario: ESPN-only owner actions labeled
- **WHEN** the owner-actions list renders
- **THEN** the Refresh League and Invite Leaguemates entries are labeled as ESPN only
