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
- **NFL state fetch fails:** log the error; avoid mass-refreshing on bad/uncertain state.
- **NFL offseason:** skip refresh runs entirely (nothing new to fetch).
- **No onboarded Sleeper leagues:** complete as a no-op.
- **Per-league invoke failure:** failures for one league must not stop the others.
- **Interaction with manual refresh cooldown:** auto-refresh must respect the same
  up-to-date / in-progress checks as [BE-002](BE-002-league-refresh.md) to avoid redundant
  or conflicting runs.
- **ESPN leagues excluded:** ESPN refresh requires user-supplied cookies, so it cannot be
  automated here — only Sleeper leagues are auto-refreshed.

## Acceptance Criteria
- [ ] During the NFL season, the Lambda invokes the onboarder in `REFRESH` mode for each
      onboarded Sleeper league.
- [ ] During the offseason or on indeterminate NFL state, no refreshes are triggered.
- [ ] A failure refreshing one league does not prevent refreshing the rest.
- [ ] ESPN leagues are not auto-refreshed.

## Sources
`src/sleeper_refresh/handler.py`, `src/sleeper_refresh/utils.py`.
