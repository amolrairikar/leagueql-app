## 1. Implementation

- [x] 1.1 In `frontend/src/features/playoff_bracket/playoff-bracket.tsx`, change the
  `BracketContent` empty-bracket check so it also treats a bracket with matches but no
  decided `winner` and no final `position` as "no renderable bracket" (routing to the
  predictor / empty-state), instead of only `matches.length === 0`. Keep the existing
  `isLatestSeason` predictor gate and let the predictor self-gate for a completed regular
  season.

## 2. Tests

- [x] 2.1 Add a scenario in `frontend/src/features/playoff_bracket/__tests__/playoff-bracket.feature`
  + `playoff-bracket.steps.test.tsx`: for the latest in-progress season, the
  `PLAYOFF_BRACKET#{season}` query returns only round-1 matches with `winner: null` and
  `position: null`; assert the predictor renders ("Playoff Picture"), not blank columns.
  Verify with `npx vitest run src/features/playoff_bracket/__tests__/playoff-bracket.steps.test.tsx`
  from `frontend/`.
- [x] 2.2 Confirm the existing "bracket renders when data loads" scenario still passes —
  a bracket with decided winners / a championship placement is unaffected.

## 3. Quality gates

- [x] 3.1 From `frontend/`, run `npm run format:fix` and `npm run lint` and verify both
  pass clean.
- [x] 3.2 Run `openspec validate fix-playoff-null-bracket-predictor --strict` and verify
  it passes.
