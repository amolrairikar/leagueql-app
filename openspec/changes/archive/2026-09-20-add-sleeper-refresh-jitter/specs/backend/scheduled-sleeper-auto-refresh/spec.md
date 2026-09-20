## ADDED Requirements

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

## MODIFIED Requirements

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
