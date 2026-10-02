# Proposal

## Why

The "Could have picked instead" panel on `/draft_grades` can suggest keepers. A keeper was never
really available: they sit in that draft slot only because the manager drafted them in that
round last year. For the same reason, a bust that was itself a keeper had no real alternatives,
since nobody else could have gone in that slot.

## What Changes

- Picks with `keeper = true` are no longer suggested as alternatives for a bust.
- A bust pick that was a keeper shows no alternatives. It still counts as a bust and keeps its
  bust marker.
- Platforms without keeper data (Yahoo sends `keeper = null`) treat every pick as a non-keeper,
  so they behave as before.

## Capabilities

### Modified Capabilities
- `frontend/draft-grades`: adds requirements that keep keepers out of the suggested
  alternatives.

## Impact

- `frontend/src/features/draft_grades/draft-grades.tsx` (`getAlts`)
- Frontend component tests under `frontend/src/features/draft_grades/__tests__/`
- No backend or API changes.
