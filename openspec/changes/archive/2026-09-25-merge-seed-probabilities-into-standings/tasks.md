## 1. Merge the tables

- [x] 1.1 In `playoff-race-predictor.tsx`, remove the `<SeedProbabilityTable />` render slot from `PredictorTool` and delete the `SeedProbabilityTable` and `SeedProbabilityRow` components (keep passing `seedProbs` to `StandingsTable`).
- [x] 1.2 In `StandingsTable`, append one right-aligned header + body column per playoff seed `1..num_playoff_teams` (after `Games left`), with a subtle left divider before the first seed column. Remove the `Win %` header and cell.
- [x] 1.3 In `StandingRowView`, drop the Win % cell; render the per-seed cells from the team's `dist` (bold the most-likely shown seed, mute `<1%`, `tabular-nums`). Update the playoff-line divider row `colSpan` to `5 + num_playoff_teams` and grow the table `minWidth` with the seed-column count.

## 2. Tests

- [x] 2.1 Update `__tests__/playoff-race-predictor.feature` + `.steps.test.tsx`: replace the standalone "Seed probabilities" scenario with assertions on the merged standings columns (seed headers present, a probability value shown, Win % gone).
- [x] 2.2 Update `src/features/demo/__tests__/demo-mode.*`: drop the separate "seed-probability section" assertion (or repoint it at the merged columns).

## 3. Validate

- [x] 3.1 From `frontend/`: `npm run format:fix` and `npm run lint` (clean).
- [x] 3.2 From `frontend/`: `npx vitest run` — full suite green.
- [x] 3.3 From repo root: `openspec validate --all`.
