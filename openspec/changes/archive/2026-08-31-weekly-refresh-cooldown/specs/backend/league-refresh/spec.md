## MODIFIED Requirements

### Requirement: Enforce refresh cooldown and concurrency
The API SHALL reject a refresh while one is already in progress and while within the once-per-week cooldown window, and SHALL update `last_refresh_at` on success. The cooldown window is a rolling 7 days measured from the most recent successful refresh.

#### Scenario: Refresh already in progress
- **WHEN** `METADATA` shows an active job and another refresh is requested
- **THEN** the API returns `409`

#### Scenario: Within cooldown window
- **WHEN** `last_refresh_at` is less than 7 days ago
- **THEN** the API returns `429` with a human-readable message stating the league can only be refreshed once per week and how long remains before it can be refreshed again

#### Scenario: Outside weekly cooldown window
- **WHEN** `last_refresh_at` is 7 or more days ago (or absent)
- **THEN** the cooldown does not block the refresh

#### Scenario: Cooldown reset on success
- **WHEN** a refresh succeeds
- **THEN** `last_refresh_at` is updated to enforce the next weekly cooldown window
