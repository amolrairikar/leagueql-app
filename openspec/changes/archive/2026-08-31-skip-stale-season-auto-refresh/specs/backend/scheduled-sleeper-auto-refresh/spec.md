## MODIFIED Requirements

### Requirement: Auto-refresh Sleeper leagues in season
During the NFL season the Lambda SHALL invoke the onboarder in `REFRESH` mode for each onboarded Sleeper league whose newest onboarded season is not behind the current NFL season, de-duplicated to one invocation per canonical league, excluding ESPN leagues.

#### Scenario: In-season refresh
- **WHEN** the run executes during the NFL season
- **THEN** it selects Sleeper leagues via the `GSI2` `platform = "SLEEPER"` partition, de-duplicates to the most recent season's `league_id` per canonical league, and invokes the onboarder in `REFRESH` mode for each

#### Scenario: ESPN excluded
- **WHEN** the run selects leagues
- **THEN** ESPN leagues are never selected (they require user-supplied cookies)

#### Scenario: Stale season skipped
- **WHEN** a canonical league's newest onboarded season is behind the current NFL season (the league has not been onboarded for the current season)
- **THEN** the run does not invoke the onboarder for that league, so a completed prior season is not re-refreshed until the league is onboarded for the current season

### Requirement: Poll pending renewal lookups
The Lambda SHALL additionally dispatch against pending renewal lookups whose `pending_season` is not behind the current NFL season, so a not-yet-started renewed season attaches automatically once it starts.

#### Scenario: Pending renewal polled
- **WHEN** a canonical league has a pending `LEAGUE_LOOKUP` (a `pending_season` marker and no `seasons`) whose `pending_season` is not behind the current NFL season
- **THEN** the run dispatches against that pending league ID too; while still `pre_draft`/`drafting` the poll is a no-op, and the first run after it flips to `in_season` promotes it to a real season (adds `seasons`, drops the marker) and builds its views

#### Scenario: Stale pending renewal skipped
- **WHEN** a pending `LEAGUE_LOOKUP` has a `pending_season` behind the current NFL season (an abandoned renewal that never started)
- **THEN** the run does not dispatch against that pending league ID

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
