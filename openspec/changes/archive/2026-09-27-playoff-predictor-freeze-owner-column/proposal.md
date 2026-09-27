## Why

On mobile, the predictor's projected standings table scrolls horizontally (projected record,
odds, PF, games left, and one column per seed). Once scrolled, the Seed · Owner column scrolls
away, so the numbers can no longer be matched to a team. The other standings tables already
freeze their owner column.

## What Changes

- Freeze the projected standings table's Seed · Owner column (header and every row) at the left
  edge while the table scrolls horizontally, matching the other standings tables.
- On mobile, cap the frozen column at a fixed width (like Season Standings' owner column) and
  wrap long names, so it can't crowd out the scrolling columns.
- Keep the playoff-line row's "Playoff line" label pinned at the left edge the same way.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `frontend/playoff-race-predictor`: adds a requirement that the Seed · Owner column stays frozen
  during horizontal scroll.

## Impact

- Frontend: `frontend/src/features/playoff_race_predictor/playoff-race-predictor.tsx`
  (`StandingsTable`, `StandingRowView`).
- Tests: `frontend/src/features/playoff_race_predictor/__tests__/playoff-race-predictor.{feature,steps.test.tsx}`.
- No backend, API-contract, or extension changes.
