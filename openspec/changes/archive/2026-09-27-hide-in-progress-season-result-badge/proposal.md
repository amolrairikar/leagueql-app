# Proposal

## Why

On `/manager_history`, every season card shows a result pill: "Champion", "Runner-up",
"Playoffs" or "Missed Playoffs". For the current, in-progress season none of these outcomes is
settled yet, but the card still shows one. Before any playoff games exist, every manager shows
"Missed Playoffs", which is wrong and misleading.

## What Changes

- A season with no finalized placement (the same in-progress test the finish fallback uses: no
  team has a `final_rank` ≥ 1) shows no result pill on its season card. The card's record,
  points, and current-standings finish still render.
- Finalized seasons are unchanged.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/manager-history`: new requirement that in-progress seasons omit the playoff-result
  pill.

## Impact

- **Frontend:**
  - `frontend/src/features/manager_history/api-calls.ts` (`withInProgressRanks` flags
    unfinalized seasons with `in_progress`)
  - `frontend/src/features/manager_history/manager-history.tsx` (season result becomes `null` for
    in-progress seasons; the badge is skipped when `null`)
  - tests: `manager_history/__tests__/manager-history.*`
- **Backend:** none.
