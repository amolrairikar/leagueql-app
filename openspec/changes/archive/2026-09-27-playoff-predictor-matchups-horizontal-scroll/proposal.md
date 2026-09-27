## Why

On mobile, the playoff-race predictor's pickable matchups run off the screen. Each team card's
owner/team name is `white-space: nowrap`, so a long name sets the matchup row's minimum width
wider than the card, and the card's `overflow-hidden` clips it.

## What Changes

- Make the pickable-matchups card horizontally scrollable. When the rows' width exceeds the
  viewport the card scrolls sideways; when they fit, nothing changes and no scrollbar appears.
- Keep every team card (avatar, names, record) the same width on mobile, as on desktop. Today a
  long name also makes its card wider than its opponent's.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `frontend/playoff-race-predictor`: adds a requirement that overflowing matchups scroll
  horizontally instead of being clipped, with equal-width team cards.

## Impact

- Frontend: `frontend/src/features/playoff_race_predictor/playoff-race-predictor.tsx` (the
  matchups card in `PredictorTool`).
- Tests: `frontend/src/features/playoff_race_predictor/__tests__/playoff-race-predictor.{feature,steps.test.tsx}`.
- No backend, API-contract, or extension changes.
