## REMOVED Requirements

### Requirement: Auto-refresh Sleeper and Yahoo leagues in season

**Reason**: Auto-refresh becomes opt-in for the credentialed platforms and now includes ESPN, so the
selection rule and its scenarios (including "ESPN excluded") are replaced by the requirement below.
**Migration**: See "Auto-refresh Sleeper and opted-in Yahoo/ESPN leagues in season" below. Sleeper
selection is unchanged; Yahoo and ESPN are selected only when the canonical league's `METADATA` has
`auto_refresh_enabled = true`.

## ADDED Requirements

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

## MODIFIED Requirements

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
