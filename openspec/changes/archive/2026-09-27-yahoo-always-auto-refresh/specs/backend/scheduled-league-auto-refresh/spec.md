## ADDED Requirements

### Requirement: Auto-refresh Sleeper, Yahoo, and opted-in ESPN leagues in season

During the NFL season the Lambda SHALL invoke the onboarder in `REFRESH` mode for each onboarded
league whose newest onboarded season is not behind the current NFL season, de-duplicated to one
invocation per canonical league. Sleeper leagues SHALL always be selected (public data). Yahoo
leagues SHALL always be selected (the owner's Yahoo authorization is stored as part of connecting,
so no opt-in is needed), subject only to having a resolvable owner; a Yahoo league's
`auto_refresh_enabled` value SHALL have no effect on whether it is selected. ESPN leagues SHALL be
selected only when the canonical league's `METADATA` item has `auto_refresh_enabled` set to true
(the owner has opted into automatic refresh); an ESPN league without that flag SHALL NOT be
selected.

#### Scenario: In-season Sleeper refresh

- **WHEN** the run executes during the NFL season
- **THEN** it selects Sleeper leagues via the `GSI2` `platform = "SLEEPER"` partition, de-duplicates
  to the most recent season's `league_id` per canonical league, and invokes the onboarder in
  `REFRESH` mode for each with no owner

#### Scenario: In-season Yahoo refresh

- **WHEN** the run executes during the NFL season and a Yahoo canonical league's `METADATA` has an
  `owner_user_id`
- **THEN** it selects that Yahoo league via the `GSI2` `platform = "YAHOO"` partition, de-duplicates
  to the most recent season's `league_id` per canonical league, and invokes the onboarder in
  `REFRESH` mode for it with the league's resolved owner

#### Scenario: Yahoo league refreshed regardless of the opt-in flag

- **WHEN** the run executes during the NFL season and a Yahoo canonical league's `METADATA` has an
  `owner_user_id` but `auto_refresh_enabled` is false or absent
- **THEN** that Yahoo league is still selected and the onboarder is invoked for it in `REFRESH` mode
  with the league's resolved owner

#### Scenario: In-season ESPN refresh, opted in

- **WHEN** the run executes during the NFL season and an ESPN canonical league's `METADATA` has
  `auto_refresh_enabled = true`
- **THEN** it selects that ESPN league via the `GSI2` `platform = "ESPN"` partition, de-duplicates to
  the most recent season's `league_id` per canonical league, and invokes the onboarder in `REFRESH`
  mode for it with the league's resolved owner and no cookies in the invoke

#### Scenario: ESPN league not opted in

- **WHEN** the run selects leagues and an ESPN canonical league's `METADATA` has no
  `auto_refresh_enabled` set to true
- **THEN** that league is not selected for refresh (ESPN auto-refresh is opt-in because enabling it
  stores the owner's cookies)

#### Scenario: Stale season skipped

- **WHEN** a canonical league's newest onboarded season is behind the current NFL season (the league
  has not been onboarded for the current season)
- **THEN** the run does not invoke the onboarder for that league, so a completed prior season is not
  re-refreshed until the league is onboarded for the current season

## REMOVED Requirements

### Requirement: Auto-refresh Sleeper and opted-in Yahoo/ESPN leagues in season

**Reason**: Yahoo leagues no longer require an opt-in; replaced by "Auto-refresh Sleeper, Yahoo, and opted-in ESPN leagues in season", which keeps the Sleeper, ESPN, and stale-season behavior unchanged.

**Migration**: None. Yahoo leagues with a resolvable owner are selected on the next in-season run regardless of their stored `auto_refresh_enabled` value; ESPN selection is unchanged.
