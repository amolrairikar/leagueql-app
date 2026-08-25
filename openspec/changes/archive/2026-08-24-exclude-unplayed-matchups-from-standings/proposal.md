## Why

The onboarder already persists every week of a season, so an in-progress season's future weeks
are stored as `0-0` placeholder matchups (`winner="TIE"`). Nothing distinguishes played from
unplayed, so these placeholders are silently counted as real tied games — inflating games/ties,
diluting win %, and corrupting every record derived from matchups. We want to keep storing the
`0-0` rows (a future live-playoff-odds simulation will replay the remaining schedule from them)
while making sure no standings or stat aggregation counts them.

## What Changes

- Backend `STANDINGS` and `WEEKLY_STANDINGS` transforms exclude regular-season matchups where
  both team scores are exactly `0` (the unplayed heuristic), so W/L/T, win %, PF/PA, per-week
  ranking, and games-played reflect only played weeks. The stored `MATCHUPS#{season}#WEEK#{week}`
  view is unchanged — the `0-0` rows remain.
- All frontend features that compute stats client-side from the raw `MATCHUPS` view exclude the
  same `0-0` unplayed rows via one shared helper (`isUnplayedMatchup`).
- No new marker column, no DynamoDB/OpenAPI schema change: only aggregation math changes.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `backend/data-processing-pipeline`: `STANDINGS`/`WEEKLY_STANDINGS` exclude unplayed (`0-0`)
  regular-season matchups from all computed metrics, while still writing the matchups view.
- `frontend/season-standings`: strength-of-schedule and expected-wins exclude unplayed matchups.
- `frontend/matchup-records`: matchup/score record leaderboards exclude unplayed matchups.
- `frontend/manager-comparison`: head-to-head records and game logs exclude unplayed matchups.
- `frontend/manager-history`: per-manager results, high scores, and rivalries exclude unplayed matchups.
- `frontend/home-dashboard`: all-time standings and total-games stats exclude unplayed matchups.
- `frontend/weekly-awards`: weekly awards, running tallies, and win streaks exclude unplayed matchups.
- `frontend/schedule-swap-simulator`: simulated records exclude unplayed matchups.
- `frontend/player-records`: player score leaderboards exclude unplayed matchups.

## Impact

- Backend: `src/processor/queries.py` (`STANDINGS`, `WEEKLY_STANDINGS`). All-time standings, summed
  client-side from per-season `STANDINGS#{season}`, are fixed transitively.
- Frontend: new `frontend/src/lib/matchups.ts` helper; guards added in the compute modules /
  aggregation loops of the eight features above.
- Tests: backend component (`tests/component`) standings scenario + fixture; frontend vitest and
  jest-cucumber scenarios.
- No API contract, DynamoDB schema, or infrastructure change.
