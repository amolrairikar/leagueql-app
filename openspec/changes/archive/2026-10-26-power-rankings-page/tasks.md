# Tasks

## 1. Scoring model

- [x] 1.1 Add `frontend/src/features/power_rankings/compute-power-rankings.ts` exposing `buildPowerRankings(matchups)` (components, scaling, fixed weights, per-cut ranks, previous rank, six-week trend, record rank, expected wins, written read); verify with `npx vitest run src/features/power_rankings`
- [x] 1.2 Add `frontend/src/features/power_rankings/__tests__/compute-power-rankings.test.ts` covering scaling, ties, unplayed/postseason exclusion, missing bench data, first-week movement, and trend length; verify the new tests pass

## 2. Page and routing

- [x] 2.1 Add `api-calls.ts` and `power-rankings.tsx` (season select, week stepper, formula section, ranking table with expandable rows, skeleton, empty and error states) in `frontend/src/features/power_rankings/`; verify in `npm run dev` and in demo mode
- [x] 2.2 Register the lazy `/power_rankings` route in `frontend/src/app/app.tsx` and add the Power Rankings entry to the sidebar nav; verify navigation works
- [x] 2.3 Add the release note to `frontend/src/features/changelog/constants.ts`

## 3. Component tests

- [x] 3.1 Add `power-rankings.feature` + `power-rankings.steps.test.tsx` (jest-cucumber, MSW) covering: rankings render, week stepper changes the table, row expands, empty state, and API error; verify with `npx vitest run src/features/power_rankings`
- [x] 3.2 Update any sidebar/navigation test that enumerates nav links; verify `npm run test:run` is green

## 4. Quality

- [x] 4.1 Run `npm run format:fix`, `npm run lint` and `npm run build:ci` from `frontend/`; verify all are clean
- [x] 4.2 Run `npx @fission-ai/openspec@latest validate --all`; verify no errors
