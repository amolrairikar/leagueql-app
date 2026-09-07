## MODIFIED Requirements

### Requirement: Refresh the current league
The sidebar SHALL expose a refresh action, shown only for ESPN leagues, pre-filled and locked to the current league and surfacing the backend cooldown/up-to-date/in-progress responses.

#### Scenario: Sidebar refresh
- **WHEN** an ESPN league owner triggers the sidebar refresh
- **THEN** the form is pre-filled and locked to the currently-viewed league, and `429`/`409` cooldown/up-to-date/in-progress responses are surfaced

#### Scenario: No refresh for Sleeper
- **WHEN** the sidebar renders for a Sleeper league
- **THEN** the Refresh League action is not shown (Sleeper leagues refresh automatically), even for the owner

### Requirement: Owner-gated sidebar actions
Owner-only actions SHALL be gated on `is_owner`, with non-owners seeing the alternate actions, and the ESPN-only actions (Refresh League, Invite Leaguemates) additionally gated on the league being an ESPN league.

#### Scenario: Owner vs non-owner actions
- **WHEN** the sidebar renders for a league
- **THEN** Migrate, Transfer Ownership, and Delete are shown only when `is_owner` is true, Refresh League and Invite Leaguemates are shown only when `is_owner` is true and the league is an ESPN league, and non-owners see View Another League and Claim Ownership instead
