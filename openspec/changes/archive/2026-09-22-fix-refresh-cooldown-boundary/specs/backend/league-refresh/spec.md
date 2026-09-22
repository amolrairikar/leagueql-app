## MODIFIED Requirements

### Requirement: Enforce refresh cooldown and concurrency
The API SHALL reject a refresh while one is already in progress and, in the PROD environment, while within the once-per-week cooldown window, and SHALL update `last_refresh_at` on success. The cooldown window is measured in whole UTC calendar days: a refresh is permitted once the current UTC date is at least 7 days after the UTC date of the most recent successful refresh, regardless of the time of day either the last refresh or the new request occurred. In the DEV environment (`ENVIRONMENT == "dev"`) the weekly cooldown does not block refreshes; the concurrency guard still applies in all environments.

#### Scenario: Refresh already in progress
- **WHEN** `METADATA` shows an active job and another refresh is requested
- **THEN** the API returns `409`

#### Scenario: Within cooldown window
- **WHEN** the most recent successful refresh was fewer than 7 UTC calendar days ago and `ENVIRONMENT` is not `dev`
- **THEN** the API returns `429` with a human-readable message stating the league can only be refreshed once per week and how long remains before it can be refreshed again

#### Scenario: Outside weekly cooldown window
- **WHEN** the most recent successful refresh's UTC date is 7 or more calendar days before the current UTC date (or `last_refresh_at` is absent)
- **THEN** the cooldown does not block the refresh

#### Scenario: Seventh day, earlier time of day
- **WHEN** `last_refresh_at` falls on a UTC date exactly 7 calendar days before the current UTC date but fewer than 7×24 hours have elapsed (e.g. the league was refreshed at 10:00 and is retried at 08:00 on the seventh day) and `ENVIRONMENT` is not `dev`
- **THEN** the cooldown does not block the refresh (no `429`)

#### Scenario: Cooldown disabled in DEV
- **WHEN** the most recent successful refresh was fewer than 7 UTC calendar days ago and `ENVIRONMENT` is `dev`
- **THEN** the cooldown does not block the refresh (no `429`) and the refresh proceeds

#### Scenario: Cooldown reset on success
- **WHEN** a refresh succeeds
- **THEN** `last_refresh_at` is updated to enforce the next weekly cooldown window
