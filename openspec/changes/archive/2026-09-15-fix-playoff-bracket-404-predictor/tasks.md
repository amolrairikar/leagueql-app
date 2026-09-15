## 1. Implementation

- [x] 1.1 In `frontend/src/features/playoff_bracket/api-calls.ts`, make `getPlayoffBracket` tolerate the backend "no data" `404` by catching an `ApiError` with `status === 404` and resolving it to `{ data: [] }`; re-throw every other error. Verify by reading the code that non-`404` errors still reject.

## 2. Tests

- [x] 2.1 Add/update a scenario in `frontend/src/features/playoff_bracket/__tests__/playoff-bracket.feature` + `playoff-bracket.steps.test.tsx`: with an MSW handler returning `404` for the `PLAYOFF_BRACKET#{season}` query on the latest in-progress season, assert the playoff-race predictor renders (not the raw `No data found` error). Verify with `npx vitest run src/features/playoff_bracket/__tests__/playoff-bracket.steps.test.tsx` from `frontend/`.
- [x] 2.2 Confirm the existing bracket-load-error behavior still holds — a non-`404` (e.g. `5xx`) bracket query still shows the fallback error — via the existing/added error scenario in the same test suite.

## 3. Quality gates

- [x] 3.1 From `frontend/`, run `npm run format:fix` and `npm run lint` and verify both pass clean.
- [x] 3.2 Run `openspec validate fix-playoff-bracket-404-predictor --strict` and verify it passes.
