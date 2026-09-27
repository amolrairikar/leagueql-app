## 1. Implementation

- [x] 1.1 In `frontend/src/features/playoff_race_predictor/playoff-race-predictor.tsx`, make the Seed · Owner `th` `sticky left-0 z-10` (on `bg-muted`) and each row's Seed · Owner `td` `sticky left-0 z-10 bg-card`, layering the playoff tint (`bg-linear-to-r from-primary/10 to-primary/10`) on playoff rows.
- [x] 1.2 Below `sm`, give the Seed · Owner `th`/`td` a fixed `w-67` (`sm:w-auto`) and let the names wrap (`overflow-wrap: anywhere`; team name `sm:truncate`).
- [x] 1.3 Make the "Playoff line" label `sticky left-3.5`.

## 2. Tests

- [x] 2.1 Extend `frontend/src/features/playoff_race_predictor/__tests__/playoff-race-predictor.{feature,steps.test.tsx}` with a scenario asserting the Seed · Owner header and cells are sticky with opaque backgrounds, and that playoff rows' frozen cells carry the tint.

## 3. Lint and verification

- [x] 3.1 From `frontend/`, run `npm run format:fix`, `npm run lint`, and the predictor tests; confirm all pass.
- [x] 3.2 Run `openspec validate --all` and confirm it passes.
