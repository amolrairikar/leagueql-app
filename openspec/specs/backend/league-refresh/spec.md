# league-refresh Specification

## Purpose
Refresh data for an already-onboarded league to pull in newly completed weeks/seasons. `POST /leagues?requestType=REFRESH` reuses the onboarder + processing pipeline but writes against the existing canonical league ID and S3 prefix, overwriting precomputed views in place. The endpoint enforces a per-league cooldown and short-circuits when the league is already up to date for the current NFL state.

## Requirements

### Requirement: Refresh an existing league
The API SHALL accept a `REFRESH` for an onboarded league, invoke the onboarder against the existing canonical league ID, and return `201`, without incrementing `LEAGUE_COUNT`.

#### Scenario: Valid refresh
- **WHEN** `POST /leagues?requestType=REFRESH` is called for an existing league that is behind current NFL state
- **THEN** the API returns `201` with a `correlation_id`, invokes the onboarder against the existing canonical league ID, and does not increment `LEAGUE_COUNT`

#### Scenario: Views overwritten in place
- **WHEN** a refresh reprocesses data
- **THEN** precomputed views are overwritten under the same canonical league ID / S3 prefix rather than duplicated

#### Scenario: Non-existent ESPN league
- **WHEN** a refresh targets an ESPN league that is not onboarded
- **THEN** the API returns `404`

### Requirement: Enforce refresh cooldown and concurrency
The API SHALL reject a refresh while one is already in progress and, in the PROD environment, while within the once-per-week cooldown window, and SHALL update `last_refresh_at` on success. The cooldown window is a rolling 7 days measured from the most recent successful refresh. In the DEV environment (`ENVIRONMENT == "dev"`) the weekly cooldown does not block refreshes; the concurrency guard still applies in all environments.

#### Scenario: Refresh already in progress
- **WHEN** `METADATA` shows an active job and another refresh is requested
- **THEN** the API returns `409`

#### Scenario: Within cooldown window
- **WHEN** `last_refresh_at` is less than 7 days ago and `ENVIRONMENT` is not `dev`
- **THEN** the API returns `429` with a human-readable message stating the league can only be refreshed once per week and how long remains before it can be refreshed again

#### Scenario: Outside weekly cooldown window
- **WHEN** `last_refresh_at` is 7 or more days ago (or absent)
- **THEN** the cooldown does not block the refresh

#### Scenario: Cooldown disabled in DEV
- **WHEN** `last_refresh_at` is less than 7 days ago and `ENVIRONMENT` is `dev`
- **THEN** the cooldown does not block the refresh (no `429`) and the refresh proceeds

#### Scenario: Cooldown reset on success
- **WHEN** a refresh succeeds
- **THEN** `last_refresh_at` is updated to enforce the next weekly cooldown window

### Requirement: Short-circuit when already up to date
The API SHALL return `409` when the league is already current, and SHALL degrade safely when NFL state cannot be fetched.

#### Scenario: NFL offseason
- **WHEN** NFL state `season_type == "off"`
- **THEN** the API returns `409` "League is already up to date (NFL offseason)."

#### Scenario: Already current
- **WHEN** the latest stored matchup `(season, week)` is `>=` current NFL state
- **THEN** the API returns `409` "League is already up to date."

#### Scenario: NFL state fetch fails
- **WHEN** the NFL state fetch fails
- **THEN** the refresh is still allowed to proceed

### Requirement: Use the user-entered ESPN season
An ESPN refresh SHALL use the user-entered `latestSeason` from the request, not the previously-onboarded season returned by `getLeague`.

#### Scenario: ESPN refresh season
- **WHEN** an ESPN league is refreshed
- **THEN** the refresh uses the user-entered latest season

### Requirement: Handle Sleeper renewals on refresh
A refresh/onboard that resolves an existing league but only a not-yet-started Sleeper season SHALL be a no-op success that registers a pending lookup, and SHALL tolerate a null bracket mid-season.

#### Scenario: Resolves only a not-yet-started season
- **WHEN** a refresh resolves an existing canonical but the latest Sleeper season `status` is `pre_draft`/`drafting`
- **THEN** it fetches no data, marks `JOB_STATUS` `COMPLETED`, and registers a **pending** `LEAGUE_LOOKUP` (new league ID → existing canonical, `pending_season` marker, no `seasons`)

#### Scenario: Poll of an already-pending league
- **WHEN** an already-pending league ID is polled while still not started (canonical passed in, chain walk skipped)
- **THEN** the pending record is left untouched

#### Scenario: Null bracket during regular season
- **WHEN** a mid-season refresh re-fetches the Sleeper bracket and receives a null body
- **THEN** the refresh succeeds with no `PLAYOFF_BRACKET#{season}` view, and a later refresh once playoffs begin fills it in

### Requirement: Owner-gated refresh
The API SHALL restrict refresh to the league owner.

#### Scenario: Non-owner refresh
- **WHEN** a non-owner calls `REFRESH`
- **THEN** the API returns `403`
