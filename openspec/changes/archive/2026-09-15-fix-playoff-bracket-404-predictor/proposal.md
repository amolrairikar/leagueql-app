## Why

The `/playoff_bracket` page renders a raw `No data found for the requested query` error for the latest in-progress season instead of the interactive playoff-race predictor it is supposed to hand off to. This directly violates the existing `frontend/playoff-bracket` spec, which requires the predictor to render when the bracket query has no matches.

## What Changes

- Treat the backend `404 "No data found for the requested query"` from the `PLAYOFF_BRACKET#{season}` query as an **empty bracket** (no matches) rather than a load error, so the empty-bracket handoff logic runs and the predictor renders for the latest in-progress season.
- Scope the tolerated-404 to the playoff-bracket query only; the matchups and weekly-standings queries keep surfacing their errors, and any non-404 failure (e.g. `5xx`) still shows the feature's fallback error message.
- Add a frontend component scenario asserting the predictor renders when the bracket query responds `404`.

No API, DynamoDB, or backend behavior changes — the backend already 404s "no data" by design; this aligns the frontend with the existing spec.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `frontend/playoff-bracket`: Clarify the "Empty-state for no bracket" requirement so that the backend's `404 "no data"` response for `PLAYOFF_BRACKET#{season}` is treated as "no matches" (the trigger for the predictor / empty-state), not as a load error.

## Impact

- `frontend/src/features/playoff_bracket/api-calls.ts` — `getPlayoffBracket` tolerates a `404`, resolving to `{ data: [] }` (mirrors the tolerated-404 pattern in `components/api/leagues.ts` `getMigrationMapping`).
- `frontend/src/features/playoff_bracket/__tests__/` — new/updated scenario + steps for the `404` → predictor path.
- No changes to `src/api/routes.py` or any backend/data contract.
