# Proposal

## Why

LeagueQL is strong on history and one-off analytics but has no weekly reason to come back. Standings
only say what already happened; managers want a "who is actually good right now" view they can argue
about every week. A power rankings page blends results with underlying strength (scoring, recent
form, lineup efficiency) and shows who is rising, falling, underrated or overrated.
Every input is already in the `MATCHUPS` view the app loads today, so the page needs no backend work.

## What Changes

- Add a `/power_rankings` page, reachable from the sidebar, with a season selector and a
  "Week N" picker. Week N shows the rankings going into week N, using every regular-season game
  played before it.
- Rank every team by a fixed-weight power score: record 35%, points scored 30%, recent form 20%,
  lineup efficiency 15%. Each part is on a 0–100 scale.
- Show per team: rank, movement since the previous week, team and manager, record, power score,
  a six-week rank trend, and where the team ranks by record alone (flagged Underrated / Overrated /
  On the mark). Expanding a row shows its per-component scores with week-over-week change, expected
  record, last week's rank, and a short written read on the team.
- Show a collapsible "How power rankings are calculated" section (collapsed by default, opened with a
  chevron) explaining how each of the four components is calculated, with its weight, followed by a worked example of league scaling.
- Compute everything on the client from the existing `MATCHUPS` query. No new API, backend,
  infrastructure, or data-model changes.
- Works in demo mode, since it reads through the same query path as the other analytics pages.

## Capabilities

### New Capabilities
- `frontend/power-rankings`: the weekly power rankings page and its client-side scoring model.

### Modified Capabilities
- `frontend/navigation-sidebar`: the sidebar links to the new Power Rankings page.

## Impact

- New `frontend/src/features/power_rankings/` (page, pure scoring module, API re-export, component
  tests). `frontend/src/app/app.tsx` (lazy route), `frontend/src/features/sidebar/app-sidebar.tsx`
  (nav entry), `frontend/src/features/changelog/constants.ts` (release note).
- Reuses `computeStartSitReport` (lineup efficiency) and `computeScheduleSwap` (schedule swap)
  rather than duplicating them.
- Tests: frontend unit tests for the scoring module and a jest-cucumber component test for the page.
  No backend tests, since the backend is unchanged.
- `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md` and the architecture diagram are
  unaffected (no new endpoint, item, or deployed component).
