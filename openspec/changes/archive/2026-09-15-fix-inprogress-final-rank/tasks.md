## 1. Implementation

- [x] 1.1 In `frontend/src/features/manager_history/api-calls.ts`, add
  `withInProgressRanks` and apply it in `getManagerHistoryData`: for a season where no
  team has a finalized placement (`final_rank` `0`/`null`) and at least one game has been
  played, set each team's `final_rank` to its current standings position (ordered by
  wins, then points-for — the backend's canonical `SEASON_STANDINGS` order). Leave
  finalized seasons unchanged, and normalize a non-positive `final_rank` to `null` for a
  season with no games yet.

## 2. Tests

- [x] 2.1 Add a scenario in
  `frontend/src/features/manager_history/__tests__/manager-history.feature` + steps: a
  manager leading an in-progress season (`final_rank: 0`, 1-0) shows finish "1st" (their
  current standings position), never "0th". This exercises the shared
  `getManagerHistoryData` logic that also feeds the home standings-position chart (the
  chart is SVG-only, so it has no reliable DOM assertion in JSDOM; the same computed
  output drives both).
- [x] 2.2 Run the affected suite(s) with `npx vitest run` from `frontend/` and verify they
  pass.

## 3. Quality gates

- [x] 3.1 From `frontend/`, run `npm run format:fix` and `npm run lint` and verify both
  pass clean.
- [x] 3.2 Run `openspec validate fix-inprogress-final-rank --strict` and verify it passes.
