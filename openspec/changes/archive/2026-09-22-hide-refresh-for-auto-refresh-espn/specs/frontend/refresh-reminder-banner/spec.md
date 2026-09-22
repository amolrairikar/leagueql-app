## MODIFIED Requirements

### Requirement: Restrict the reminder audience
The banner SHALL NOT render for Sleeper leagues, for non-owners, in demo mode, when no league is connected, while the league's freshness is still loading, or for ESPN leagues enrolled in auto-refresh (`auto_refresh_enabled` true).

#### Scenario: Sleeper league
- **WHEN** the current league is on the Sleeper platform
- **THEN** the banner does not appear regardless of freshness

#### Scenario: Non-owner viewer
- **WHEN** the caller is not the league owner
- **THEN** the banner does not appear

#### Scenario: Demo mode
- **WHEN** the app is in demo mode
- **THEN** the banner does not appear

#### Scenario: Freshness loading
- **WHEN** the league's freshness data has not yet loaded
- **THEN** the banner does not appear

#### Scenario: Auto-refresh-enabled ESPN league
- **WHEN** the current ESPN league's `auto_refresh_enabled` is true, even if its data is stale
- **THEN** the banner does not appear (the league refreshes automatically, and the Refresh League action it points at is hidden)
