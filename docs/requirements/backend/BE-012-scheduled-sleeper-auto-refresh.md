# BE-012: Scheduled Sleeper Auto-Refresh

## Description
Scheduled Lambda that automatically refreshes onboarded Sleeper leagues during the NFL
season so users see up-to-date data without manually triggering a refresh. Checks current
NFL state, enumerates onboarded Sleeper leagues, and invokes the onboarder Lambda in
`REFRESH` mode for each.

## Scope
- Lambda: `src/sleeper_refresh/` (`handler.py`, `utils.py`).
- Helpers: `get_nfl_state`, `get_sleeper_leagues`, `invoke_onboarder_lambda`.

## Edge Cases
- **NFL state fetch fails:** log the error and **raise** (do not mass-refresh on bad/uncertain
  state). Raising surfaces the run as a Lambda error so the `sleeper_refresh_errors` alarm
  fires; previously the handler returned a `502`, which left the metric flat and the failed
  run invisible.
- **League-list query fails:** log and **raise** for the same reason — a query failure
  refreshes zero leagues, so it must trip the error alarm rather than report success.
- **NFL offseason / week 1:** skip refresh runs entirely (nothing new / matchups unsettled);
  these are legitimate no-ops and return `skipped` without raising.
- **No onboarded Sleeper leagues:** complete as a no-op (`succeeded`, no raise).
- **Per-league invoke failure:** failures for one league must not stop the others — every
  league is attempted. If **any** dispatch failed, the handler then **raises** after the loop
  so the error alarm fires and EventBridge retries the run (re-attempting the failed
  dispatches). A dispatch failure never reaches the onboarder, so neither the onboarder error
  alarm nor its DLQ would otherwise catch it.
- **Interaction with manual refresh cooldown:** auto-refresh must respect the same
  up-to-date / in-progress checks as [BE-002](BE-002-league-refresh.md) to avoid redundant
  or conflicting runs.
- **ESPN leagues excluded:** ESPN refresh requires user-supplied cookies, so it cannot be
  automated here — only Sleeper leagues are auto-refreshed.

## Acceptance Criteria
- [ ] During the NFL season, the Lambda invokes the onboarder in `REFRESH` mode for each
      onboarded Sleeper league.
- [ ] Leagues are selected by querying the Sleeper-platform partition of `GSI2`
      (`platform = "SLEEPER"`) and de-duplicated to one invocation per canonical league
      (the most recent season's `league_id`); ESPN leagues are therefore never selected.
- [ ] During the offseason (`season_type == "off"`) **or** in week 1 (matchups not yet
      settled), the run is skipped with status `skipped` and no onboarder invocations.
- [ ] On indeterminate NFL state (state fetch fails), no refreshes are triggered and the
      handler raises so the `sleeper_refresh_errors` alarm fires.
- [ ] A league-list query failure raises (zero leagues refreshed) rather than reporting success.
- [ ] A failure refreshing one league does not prevent refreshing the rest; if any league
      dispatch failed, the run raises after attempting all leagues so the error alarm fires.
- [ ] ESPN leagues are not auto-refreshed.

## Sources
`src/sleeper_refresh/handler.py`, `src/sleeper_refresh/utils.py`.
