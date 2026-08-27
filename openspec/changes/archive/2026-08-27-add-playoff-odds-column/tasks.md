## 1. Odds engine

- [x] 1.1 In `frontend/src/features/playoff_race_predictor/compute-projection.ts`, add a small seeded PRNG helper (mulberry32) and scenario constants (`MAX_EXACT_MATCHUPS`, `MONTE_CARLO_SAMPLES`).
- [x] 1.2 Add exported `computePlayoffOdds(model, picks)` returning `Map<teamId, number>` in `[0,1]`: build the fixed base (baseline + applied picks, with fixed points-for), collect unpicked matchups as free win/loss bits, and tally top-`num_playoff_teams` membership over outcomes — exact enumeration over all `2^N` masks when `N ≤ MAX_EXACT_MATCHUPS` (the `N === 0` case falls out as a single scenario), seeded Monte Carlo otherwise. Reuse the same seeding rule as `compareRecords` (wins desc, then fixed points-for desc, then team id).
- [x] 1.3 Add unit tests in `__tests__/compute-projection.test.ts`: two otherwise-tied teams with one game between them → 0.5 each; a clinched team → 1.0 and an eliminated team → 0.0; a small hand-verifiable multi-game enumeration; odds shift and become conditional after a pick; `N === 0` deterministic; a medium case exercising the seeded sampling path (deterministic, close to exact). Run `npx vitest run src/features/playoff_race_predictor/__tests__/compute-projection.test.ts`.

## 2. Standings table column

- [x] 2.1 In `playoff-race-predictor.tsx` `StandingsTable`, compute `odds` in its own `useMemo(() => computePlayoffOdds(model, picks), [model, picks])`, add a `Playoff odds` `<th>` (after "Proj. record"), pass per-team odds into `StandingRowView`, and render a right-aligned `tabular-nums` `<td>` with a format helper (`100%`/`0%` exact, `<1%`/`>99%` extremes, integer % otherwise, `—` if absent).
- [x] 2.2 Bump the playoff-line divider `colSpan={5}` → `6`, widen the table `minWidth`, and update the footer note to explain the coin-flip/all-outcomes semantics.
- [x] 2.3 Add/extend a jest-cucumber scenario in `__tests__/playoff-race-predictor.feature` + `.steps.test.tsx` asserting the odds column renders a `%` and updates after picking a winner. Run `npx vitest run src/features/playoff_race_predictor/__tests__/`.

## 3. Validate

- [x] 3.1 From `frontend/`: `npm run lint` and `npm run format:fix`.
- [x] 3.2 From repo root: `openspec validate --all`.
