## MODIFIED Requirements

### Requirement: Refresh the current league
The sidebar SHALL expose a refresh action, shown only for ESPN leagues that are not enrolled in
auto-refresh (`auto_refresh_enabled` false or absent), pre-filled and locked to the current league
and surfacing the backend cooldown/up-to-date/in-progress responses.

#### Scenario: Sidebar refresh
- **WHEN** an ESPN league owner of a league not enrolled in auto-refresh triggers the sidebar refresh
- **THEN** the form is pre-filled and locked to the currently-viewed league, and `429`/`409` cooldown/up-to-date/in-progress responses are surfaced

#### Scenario: No refresh for Sleeper
- **WHEN** the sidebar renders for a Sleeper league
- **THEN** the Refresh League action is not shown (Sleeper leagues refresh automatically), even for the owner

#### Scenario: No refresh for auto-refresh-enabled ESPN leagues
- **WHEN** the sidebar renders for an ESPN league whose `auto_refresh_enabled` is true
- **THEN** the Refresh League action is not shown (the league refreshes automatically on a schedule), even for the owner

### Requirement: Owner-gated sidebar actions
Owner-only actions SHALL be gated on `is_owner`, with non-owners seeing the alternate actions. Invite Leaguemates SHALL additionally be gated on the league being an ESPN league, and Refresh League SHALL additionally be gated on the league being an ESPN league that is not enrolled in auto-refresh.

#### Scenario: Owner vs non-owner actions
- **WHEN** the sidebar renders for a league
- **THEN** Migrate, Transfer Ownership, and Delete are shown only when `is_owner` is true, Invite Leaguemates is shown only when `is_owner` is true and the league is an ESPN league, Refresh League is shown only when `is_owner` is true and the league is an ESPN league whose `auto_refresh_enabled` is false, and non-owners see View Another League and Claim Ownership instead
