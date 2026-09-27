## Why

On mobile, the matchup preview's Top Scorers card places both teams' lists side by side in two
narrow columns, squeezing player names into heavy truncation.

## What Changes

- Below the `sm` breakpoint, stack the two teams' top-scorer lists vertically (left team above
  the right team, separated by a divider); keep the side-by-side layout from `sm` up.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `frontend/matchup-previews`: the Top scorers requirement specifies the responsive layout.

## Impact

- Frontend: `frontend/src/features/matchups/matchup-preview.tsx` (`TopScorersColumn` and the Top
  Scorers card grid).
- Tests: `frontend/src/features/matchups/__tests__/matchups.{feature,steps.test.tsx}`.
- No backend, API-contract, or extension changes.
