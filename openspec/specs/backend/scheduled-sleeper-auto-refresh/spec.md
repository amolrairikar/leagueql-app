# scheduled-sleeper-auto-refresh Specification

## Purpose
Scheduled Lambda that automatically refreshes onboarded Sleeper leagues during the NFL season so users see up-to-date data without triggering a refresh manually. It checks current NFL state, enumerates onboarded Sleeper leagues, and invokes the onboarder Lambda in `REFRESH` mode for each.

## Requirements

### Requirement: Auto-refresh Sleeper leagues in season
During the NFL season the Lambda SHALL invoke the onboarder in `REFRESH` mode for each onboarded Sleeper league whose newest onboarded season is not behind the current NFL season, de-duplicated to one invocation per canonical league, excluding ESPN leagues. The per-league invocations SHALL be staggered across the jitter window rather than fired in an immediate loop.

#### Scenario: In-season refresh
- **WHEN** the run executes during the NFL season
- **THEN** it selects Sleeper leagues via the `GSI2` `platform = "SLEEPER"` partition, de-duplicates to the most recent season's `league_id` per canonical league, and invokes the onboarder in `REFRESH` mode for each, spread across the randomized jitter window

#### Scenario: ESPN excluded
- **WHEN** the run selects leagues
- **THEN** ESPN leagues are never selected (they require user-supplied cookies)

#### Scenario: Stale season skipped
- **WHEN** a canonical league's newest onboarded season is behind the current NFL season (the league has not been onboarded for the current season)
- **THEN** the run does not invoke the onboarder for that league, so a completed prior season is not re-refreshed until the league is onboarded for the current season

### Requirement: Spread refresh dispatches with jitter
The Lambda SHALL spread the per-league onboarder invocations across a bounded, randomized time window (jitter) rather than dispatching them all at once, so the Sleeper API is not hit simultaneously. The window SHALL be configurable, default approximately ten minutes; a window of `0` (or a run with a single league) SHALL dispatch immediately with no added delay. The total added delay across a run SHALL NOT exceed the configured window regardless of how many leagues are selected.

#### Scenario: Multiple leagues staggered
- **WHEN** the run selects more than one league and the jitter window is greater than `0`
- **THEN** each league's onboarder invocation is delayed by a random offset within the window, so the invocations are spread over time rather than fired back-to-back, and the run's total added delay does not exceed the configured window

#### Scenario: Jitter disabled or single league
- **WHEN** the jitter window is configured to `0`, or the run selects only one league
- **THEN** the onboarder invocations are dispatched immediately with no added delay

#### Scenario: Every selected league still dispatched
- **WHEN** jitter is applied to a run
- **THEN** every selected league is still invoked in `REFRESH` mode exactly as it would be without jitter, and the existing per-league failure isolation (attempt all leagues, raise after the loop if any dispatch failed) is unchanged

### Requirement: Poll pending renewal lookups
The Lambda SHALL additionally dispatch against pending renewal lookups whose `pending_season` is not behind the current NFL season, so a not-yet-started renewed season attaches automatically once it starts.

#### Scenario: Pending renewal polled
- **WHEN** a canonical league has a pending `LEAGUE_LOOKUP` (a `pending_season` marker and no `seasons`) whose `pending_season` is not behind the current NFL season
- **THEN** the run dispatches against that pending league ID too; while still `pre_draft`/`drafting` the poll is a no-op, and the first run after it flips to `in_season` promotes it to a real season (adds `seasons`, drops the marker) and builds its views

#### Scenario: Stale pending renewal skipped
- **WHEN** a pending `LEAGUE_LOOKUP` has a `pending_season` behind the current NFL season (an abandoned renewal that never started)
- **THEN** the run does not dispatch against that pending league ID

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

#### Scenario: NFL state missing season
- **WHEN** NFL state lacks a parseable `season` value
- **THEN** no refreshes are triggered and the handler raises so the error alarm fires, rather than proceeding without a current-season reference

#### Scenario: League-list query fails
- **WHEN** the league-list query fails
- **THEN** the handler raises (zero leagues refreshed) rather than reporting success

### Requirement: Isolate per-league failures
The Lambda SHALL attempt every league even if one dispatch fails, and raise after the loop if any dispatch failed so EventBridge retries.

#### Scenario: One league dispatch fails
- **WHEN** dispatching a refresh for one league fails
- **THEN** the remaining leagues are still attempted, and after the loop the run raises so the error alarm fires and the run is retried
