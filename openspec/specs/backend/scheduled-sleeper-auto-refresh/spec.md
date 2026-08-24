# scheduled-sleeper-auto-refresh Specification

## Purpose
Scheduled Lambda that automatically refreshes onboarded Sleeper leagues during the NFL season so users see up-to-date data without triggering a refresh manually. It checks current NFL state, enumerates onboarded Sleeper leagues, and invokes the onboarder Lambda in `REFRESH` mode for each.

## Requirements

### Requirement: Auto-refresh Sleeper leagues in season
During the NFL season the Lambda SHALL invoke the onboarder in `REFRESH` mode for each onboarded Sleeper league, de-duplicated to one invocation per canonical league, excluding ESPN leagues.

#### Scenario: In-season refresh
- **WHEN** the run executes during the NFL season
- **THEN** it selects Sleeper leagues via the `GSI2` `platform = "SLEEPER"` partition, de-duplicates to the most recent season's `league_id` per canonical league, and invokes the onboarder in `REFRESH` mode for each

#### Scenario: ESPN excluded
- **WHEN** the run selects leagues
- **THEN** ESPN leagues are never selected (they require user-supplied cookies)

### Requirement: Poll pending renewal lookups
The Lambda SHALL additionally dispatch against pending renewal lookups so a not-yet-started renewed season attaches automatically once it starts.

#### Scenario: Pending renewal polled
- **WHEN** a canonical league has a pending `LEAGUE_LOOKUP` (a `pending_season` marker and no `seasons`)
- **THEN** the run dispatches against that pending league ID too; while still `pre_draft`/`drafting` the poll is a no-op, and the first run after it flips to `in_season` promotes it to a real season (adds `seasons`, drops the marker) and builds its views

### Requirement: Skip legitimate no-op windows
The Lambda SHALL skip the run without raising during the offseason or in week 1, and complete as a no-op when there are no onboarded Sleeper leagues.

#### Scenario: Offseason or week 1
- **WHEN** NFL state `season_type == "off"` or it is week 1 (matchups not yet settled)
- **THEN** the run returns status `skipped` with no onboarder invocations and does not raise

#### Scenario: No Sleeper leagues
- **WHEN** there are no onboarded Sleeper leagues
- **THEN** the run completes as a no-op (`succeeded`) without raising

### Requirement: Raise on indeterminate state or query failure
The Lambda SHALL raise (tripping the `sleeper_refresh_errors` alarm) when NFL state is indeterminate or the league-list query fails, rather than mass-refreshing or reporting false success.

#### Scenario: NFL state fetch fails
- **WHEN** the NFL state fetch fails
- **THEN** no refreshes are triggered and the handler raises so the error alarm fires

#### Scenario: League-list query fails
- **WHEN** the league-list query fails
- **THEN** the handler raises (zero leagues refreshed) rather than reporting success

### Requirement: Isolate per-league failures
The Lambda SHALL attempt every league even if one dispatch fails, and raise after the loop if any dispatch failed so EventBridge retries.

#### Scenario: One league dispatch fails
- **WHEN** dispatching a refresh for one league fails
- **THEN** the remaining leagues are still attempted, and after the loop the run raises so the error alarm fires and the run is retried
