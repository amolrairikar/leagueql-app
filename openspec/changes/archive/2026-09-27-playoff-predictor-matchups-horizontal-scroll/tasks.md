## 1. Implementation

- [x] 1.1 In `frontend/src/features/playoff_race_predictor/playoff-race-predictor.tsx`, change the matchups card from `overflow-hidden` to `overflow-x-auto` and size its inner row column `w-max min-w-full` so the team cards stay equal width.

## 2. Tests

- [x] 2.1 Extend `frontend/src/features/playoff_race_predictor/__tests__/playoff-race-predictor.{feature,steps.test.tsx}` with a scenario asserting the week's matchups render in a horizontally scrollable container whose row column is sized `w-max min-w-full`.

## 3. Lint and verification

- [x] 3.1 From `frontend/`, run `npm run format:fix`, `npm run lint`, and the predictor tests; confirm all pass.
- [x] 3.2 Run `openspec validate --all` and confirm it passes.
