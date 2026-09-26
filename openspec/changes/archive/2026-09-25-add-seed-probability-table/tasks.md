## 1. Seed-probability engine

- [x] 1.1 In `frontend/src/features/playoff_race_predictor/compute-projection.ts`, add exported `computeSeedProbabilities(model, picks): Map<string, number[]>`, mirroring the `computePlayoffOdds` setup (baseWins with picks folded in, fixed points-for `tieRank`, `freeA`/`freeB` for un-picked matchups, exact-vs-Monte-Carlo branch). Accumulate a per-seed matrix (`Float64Array(n * n)`): for each team compute `above` exactly as `tallyScenario` does and increment `seedCounts[i * n + above]`. Return each team's length-`n` array normalized by the scenario count (index `0` = seed 1).
- [x] 1.2 Refactor `computePlayoffOdds` to derive from `computeSeedProbabilities` — sum each team's entries `0..num_playoff_teams-1`. Output must be identical to today's `Map<string, number>` so existing tests stay green.
- [x] 1.3 Unit tests in `__tests__/compute-projection.test.ts`: each team's distribution sums to ~1; a small hand-checkable scenario with known finishing ranks (including a fixed points-for tiebreak between equal records); and a consistency check that summing the top-`num_playoff_teams` seeds equals `computePlayoffOdds` for the same model/picks.

## 2. Seed-probability UI

- [x] 2.1 In `playoff-race-predictor.tsx`, compute the matrix once in `PredictorTool` (`useMemo(() => computeSeedProbabilities(model, picks), [model, picks])`) and pass it to `StandingsTable` and a new `SeedProbabilityTable`.
- [x] 2.2 Update `StandingsTable` to take the shared `seedProbs` and derive its "Playoff odds" column by summing the top-`num_playoff_teams` slice (drop its own `computePlayoffOdds` call).
- [x] 2.3 Add `SeedProbabilityTable` rendered between `<StandingsTable />` and `<ClinchScenarios />`. Card + table mirror `StandingsTable` (`bg-card border border-border/50 rounded-lg overflow-hidden mt-5`, eyebrow label "Seed probabilities" + subcaption, `overflow-x-auto`, `minWidth` scaling with column count). Columns: `Seed · Owner`, one right-aligned column per seed `1..num_playoff_teams`, then `Miss` (sum of ranks `num_playoff_teams..n-1`) with a subtle left divider echoing the playoff line. Rows follow `projectStandings(model, picks)` order; reuse `TeamAvatar`, `avatarColor`, `cn`, `formatOdds`. Bold each team's most-likely bucket, mute `<1%`, `tabular-nums`. Show the "(assumed)" caveat when `numPlayoffTeamsAssumed`.
- [x] 2.4 Add a jest-cucumber scenario in `__tests__/playoff-race-predictor.feature` + `.steps.test.tsx`: the "Seed probabilities" table renders with the seed column headers and a Miss column and shows a probability value; reuse the existing `IN_PROGRESS`/`SETTINGS` fixtures and `leagueQuery(...)` MSW helper.

## 3. Demo (replay) mode

- [x] 3.1 Confirm the table renders in demo replay over `src/lib/demo-data.json` and extend `src/features/demo/__tests__/demo-mode.*` to assert it.

## 4. Validate

- [x] 4.1 From `frontend/`: `npm run format:fix` and `npm run lint` (clean).
- [x] 4.2 From `frontend/`: `npx vitest run` — full suite green.
- [x] 4.3 From repo root: `openspec validate --all`.
