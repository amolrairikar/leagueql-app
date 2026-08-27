## Why

While a league's current season is still in its regular season, the Playoff Bracket page has nothing to show —
there is no bracket yet, so it renders a plain "No playoff bracket for this season yet" message. That dead space
is the moment managers most want to explore the playoff race. We can turn it into an interactive **playoff-race
predictor**: pick the winners of the remaining regular-season games and watch a projected standings table
re-sort live around the playoff cutoff.

## What Changes

- Replace the Playoff Bracket page's in-progress empty state with an interactive predictor: a week stepper of
  the remaining regular-season matchups, click-to-pick winners, and a projected standings table that re-sorts
  live with a dashed playoff-cutoff line, movement arrows, and a clinched indicator.
- The predictor computes records, points-for, and team display entirely from existing `MATCHUPS` data. It runs
  in two modes: **live** (a real in-progress season) and **replay** (demo mode, over the last 3 regular-season
  weeks of the completed demo season).
- Persist a new per-season **`LEAGUE_SETTINGS`** precomputed view holding `num_playoff_teams`,
  `playoff_week_start`, and `regular_season_weeks`, extracted by the processor from platform settings already
  stored in S3 (Sleeper `settings.playoff_teams` / `settings.playoff_week_start`; ESPN
  `settings.scheduleSettings.playoffTeamCount` / `matchupPeriodCount`). Default `num_playoff_teams` to 6 when a
  platform omits it. This is required because the playoff-team count cannot be inferred mid-season (no bracket
  exists yet).
- Expose that view through the existing query endpoint via a new `LEAGUE_SETTINGS` queryType.
- In demo mode only, show a `Bracket / Playoff Race` toggle on the bracket page and seed `LEAGUE_SETTINGS`
  rows into the demo dataset.

## Capabilities

### New Capabilities
- `frontend/playoff-race-predictor`: the interactive predictor that lets a user pick remaining regular-season
  winners and see a live-updating projected-standings table with a playoff cutoff line; its projection rules
  (records entering each week, sort order, cutoff, movement, clinch) and its live/replay modes.

### Modified Capabilities
- `backend/data-processing-pipeline`: the processor additionally extracts per-season league settings from the
  Sleeper/ESPN settings payloads and persists a `LEAGUE_SETTINGS#{season}` view item.
- `backend/query-precomputed-views`: the query endpoint gains a `LEAGUE_SETTINGS` queryType that returns the
  per-season settings view.
- `frontend/playoff-bracket`: the in-progress empty state delegates to the live predictor when the selected
  season is the latest season and the regular season is still in progress; otherwise it keeps the existing
  empty message, and completed-season bracket rendering is unchanged.
- `frontend/demo-mode`: the demo bracket page exposes a Bracket / Playoff Race toggle (replay mode over the
  last 3 regular-season weeks), and the demo dataset includes the new settings view.

## Impact

- Backend: `src/processor/handler.py` (new `EntityType` + per-season settings extraction and key schema),
  `src/api/routes.py` (queryType enum + SK map). Docs: `docs/api/openapi_spec.yaml` queryType enum,
  `docs/db/dynamodb_spec.md` new item.
- Frontend: new `frontend/src/features/playoff_race_predictor/`, edits to
  `frontend/src/features/playoff_bracket/playoff-bracket.tsx`, a new `LeagueSettingsItem` type, and a small
  export of `isRegularSeason` from `compute-schedule-swap.ts` for reuse.
- Demo: `scripts/utility_scripts/seed_demo_data.py` emits `LEAGUE_SETTINGS` rows (regenerating the committed
  `frontend/src/lib/demo-data.json`); `frontend/src/lib/demo-api.ts` maps the new queryType.
- Tests: backend unit + component (settings extraction and queryType); frontend unit (`compute-projection`) +
  jest-cucumber scenarios for the predictor, the bracket delegation, and the demo toggle.
- No infrastructure or architecture-diagram change (no new deployed component).
