# scheduled-league-auto-refresh Specification

## Purpose
Scheduled Lambda that automatically refreshes onboarded Sleeper and Yahoo leagues during the NFL season so users see up-to-date data without triggering a refresh manually. It checks current NFL state, enumerates onboarded leagues per platform, paces dispatches so downstream onboarders do not burst a platform's API, and invokes the onboarder Lambda in `REFRESH` mode for each.

## Requirements

### Requirement: Resolve the Yahoo owner and dispatch as the owner

For each selected Yahoo or ESPN league, the Lambda SHALL resolve the canonical league's
`owner_user_id` from its `METADATA` item and pass it in the onboarder invoke, so the onboarder can
obtain the owner's stored credentials — the owner's Yahoo OAuth token for Yahoo, or the owner's
stored ESPN cookies for ESPN. A Yahoo or ESPN league whose `METADATA` has no `owner_user_id` SHALL
be skipped (it cannot be refreshed without an owner). The ESPN invoke SHALL NOT carry cookies; the
onboarder fetches the owner's stored ESPN cookies itself.

#### Scenario: Yahoo owner resolved and passed through

- **WHEN** a selected Yahoo or ESPN league's `METADATA` item has an `owner_user_id`
- **THEN** the onboarder is invoked for that league with its `platform` and that `owner_user_id`, and
  for ESPN with no cookies in the invoke

#### Scenario: Yahoo league without an owner skipped

- **WHEN** a selected Yahoo or ESPN league's `METADATA` item is missing or has no `owner_user_id`
- **THEN** the run does not invoke the onboarder for that league and continues with the others

### Requirement: Pace dispatches within a platform
The Lambda SHALL wait a configurable base interval plus a random jitter between consecutive onboarder dispatches to the same platform, so the fanned-out onboarder invocations do not hit a platform's API simultaneously. The base interval and maximum jitter SHALL be configurable, with modest defaults, and no wait is required after the last dispatch of a platform or between platform groups.

#### Scenario: Consecutive same-platform dispatches are spaced
- **WHEN** the run dispatches more than one league for a platform
- **THEN** it waits the configured base interval plus a random jitter between each consecutive dispatch for that platform

#### Scenario: No wait after the final dispatch
- **WHEN** the run dispatches the last league for a platform
- **THEN** it does not wait after that dispatch

### Requirement: Poll pending renewal lookups
The Lambda SHALL additionally dispatch against pending Sleeper renewal lookups whose `pending_season` is not behind the current NFL season, so a not-yet-started renewed season attaches automatically once it starts.

#### Scenario: Pending renewal polled
- **WHEN** a canonical Sleeper league has a pending `LEAGUE_LOOKUP` (a `pending_season` marker and no `seasons`) whose `pending_season` is not behind the current NFL season
- **THEN** the run dispatches against that pending league ID too; while still `pre_draft`/`drafting` the poll is a no-op, and the first run after it flips to `in_season` promotes it to a real season (adds `seasons`, drops the marker) and builds its views

#### Scenario: Stale pending renewal skipped
- **WHEN** a pending `LEAGUE_LOOKUP` has a `pending_season` behind the current NFL season (an abandoned renewal that never started)
- **THEN** the run does not dispatch against that pending league ID

### Requirement: Skip legitimate no-op windows
The Lambda SHALL skip the run without raising during the offseason or in week 1, and complete as a no-op when there are no onboarded Sleeper or Yahoo leagues.

#### Scenario: Offseason or week 1
- **WHEN** NFL state `season_type == "off"` or it is week 1 (matchups not yet settled)
- **THEN** the run returns status `skipped` with no onboarder invocations and does not raise

#### Scenario: No leagues to refresh
- **WHEN** there are no onboarded Sleeper or Yahoo leagues to refresh
- **THEN** the run completes as a no-op (`succeeded`) without raising

### Requirement: Raise on indeterminate state or query failure
The Lambda SHALL raise (tripping the refresher's error alarm) when NFL state is indeterminate or a league-list query fails, rather than mass-refreshing or reporting false success.

#### Scenario: NFL state fetch fails
- **WHEN** the NFL state fetch fails
- **THEN** no refreshes are triggered and the handler raises so the error alarm fires

#### Scenario: NFL state missing season
- **WHEN** NFL state lacks a parseable `season` value
- **THEN** no refreshes are triggered and the handler raises so the error alarm fires, rather than proceeding without a current-season reference

#### Scenario: League-list query fails
- **WHEN** a league-list query fails
- **THEN** the handler raises (zero leagues refreshed) rather than reporting success

### Requirement: Isolate per-league failures
The Lambda SHALL attempt every league even if one dispatch fails, and raise after the loop if any dispatch failed so EventBridge retries.

#### Scenario: One league dispatch fails
- **WHEN** dispatching a refresh for one league fails
- **THEN** the remaining leagues are still attempted, and after the loop the run raises so the error alarm fires and the run is retried

### Requirement: Auto-refresh Sleeper and opted-in Yahoo/ESPN leagues in season

During the NFL season the Lambda SHALL invoke the onboarder in `REFRESH` mode for each onboarded
league whose newest onboarded season is not behind the current NFL season, de-duplicated to one
invocation per canonical league. Sleeper leagues SHALL always be selected (public data). Yahoo and
ESPN leagues SHALL be selected only when the canonical league's `METADATA` item has
`auto_refresh_enabled` set to true (the owner has opted into automatic refresh); a Yahoo or ESPN
league without that flag SHALL NOT be selected.

#### Scenario: In-season Sleeper refresh

- **WHEN** the run executes during the NFL season
- **THEN** it selects Sleeper leagues via the `GSI2` `platform = "SLEEPER"` partition, de-duplicates
  to the most recent season's `league_id` per canonical league, and invokes the onboarder in
  `REFRESH` mode for each with no owner

#### Scenario: In-season Yahoo refresh, opted in

- **WHEN** the run executes during the NFL season and a Yahoo canonical league's `METADATA` has
  `auto_refresh_enabled = true`
- **THEN** it selects that Yahoo league via the `GSI2` `platform = "YAHOO"` partition, de-duplicates
  to the most recent season's `league_id` per canonical league, and invokes the onboarder in
  `REFRESH` mode for it with the league's resolved owner

#### Scenario: In-season ESPN refresh, opted in

- **WHEN** the run executes during the NFL season and an ESPN canonical league's `METADATA` has
  `auto_refresh_enabled = true`
- **THEN** it selects that ESPN league via the `GSI2` `platform = "ESPN"` partition, de-duplicates to
  the most recent season's `league_id` per canonical league, and invokes the onboarder in `REFRESH`
  mode for it with the league's resolved owner and no cookies in the invoke

#### Scenario: Yahoo or ESPN league not opted in

- **WHEN** the run selects leagues and a Yahoo or ESPN canonical league's `METADATA` has no
  `auto_refresh_enabled` set to true
- **THEN** that league is not selected for refresh (auto-refresh is opt-in for credentialed platforms)

#### Scenario: Stale season skipped

- **WHEN** a canonical league's newest onboarded season is behind the current NFL season (the league
  has not been onboarded for the current season)
- **THEN** the run does not invoke the onboarder for that league, so a completed prior season is not
  re-refreshed until the league is onboarded for the current season

### Requirement: Manage per-league auto-refresh enrollment

The API SHALL let a league's owner turn automatic refresh on or off for that league via
`PUT /leagues/{leagueId}/auto-refresh` with an `enabled` boolean, restricting the action to the
league owner and persisting the choice as `auto_refresh_enabled` on the canonical league's
`METADATA` item. When a change leaves the owner with no ESPN league opted into automatic refresh,
the API SHALL delete the owner's stored ESPN credentials.

#### Scenario: Owner enables auto-refresh

- **WHEN** a league owner calls `PUT /leagues/{leagueId}/auto-refresh` with `enabled = true`
- **THEN** the canonical league's `METADATA` `auto_refresh_enabled` is set to true and the API
  returns `200`

#### Scenario: Owner disables auto-refresh

- **WHEN** a league owner calls `PUT /leagues/{leagueId}/auto-refresh` with `enabled = false`
- **THEN** the canonical league's `METADATA` `auto_refresh_enabled` is cleared and the API returns
  `200`

#### Scenario: Disabling the last opted-in ESPN league removes stored cookies

- **WHEN** an owner disables auto-refresh for their last ESPN league that was opted in
- **THEN** their stored `ESPN_CREDENTIALS` item is deleted

#### Scenario: Non-owner rejected

- **WHEN** a user who is not the league owner calls `PUT /leagues/{leagueId}/auto-refresh`
- **THEN** the API returns `403` and `auto_refresh_enabled` is not changed
