## Why

The playoff-race predictor shows a projected-standings table with a single **playoff-odds** column
— each team's chance of landing in *any* top-`num_playoff_teams` seed. That answers "will they make
it", but not "*where* will they land". Managers care about the difference: a first-round bye, home
field, or a specific matchup all hinge on the exact seed, not just make/miss. The enumeration that
already powers the odds column computes each team's exact finishing rank in every remaining outcome
— it just collapses that rank to a make/miss bit. Keeping the full distribution gives a much richer
picture for free.

## What Changes

- Add a **Seed probabilities** table directly below the projected-standings table (and above the
  clinching-scenarios section). Each team is a row; each playoff seed `1..num_playoff_teams` is a
  column, plus a final **Miss** column for finishing outside the playoffs. Every row sums to ~100%.
- Values are the share of remaining outcomes in which the team finishes in that exact seed, computed
  over the **same enumeration** the playoff odds already use (each un-picked matchup an equally
  likely 50/50, points-for fixed as tiebreak only), **conditional on the user's picks**, exact when
  the un-picked space is small enough and sampled otherwise.
- The existing playoff-odds column is **preserved** — it now derives from the per-seed distribution
  (sum of the top-`num_playoff_teams` seeds), so odds and seed probabilities are guaranteed
  consistent and the page enumerates the outcome space once instead of twice.
- Cells are plain numbers (reusing the existing `<1%` / `>99%` / integer-% formatting); each team's
  most-likely bucket is emphasized and sub-1% values are muted.
- Included in demo (replay) mode automatically, since the table lives in the shared predictor tool
  and the demo dataset already provides the settings/matchup data it needs.

## Capabilities

### Modified Capabilities
- `frontend/playoff-race-predictor`: the projected-standings view gains a per-team seed-probability
  table (one column per playoff seed plus a Miss column), computed over the same un-picked-outcome
  enumeration as the playoff odds and conditional on the user's picks; the playoff-odds column is
  redefined as the sum of a team's top-`num_playoff_teams` seed probabilities.

## Impact

- **Frontend only.** No backend / API / DynamoDB / infrastructure / architecture-diagram change.
- `frontend/src/features/playoff_race_predictor/compute-projection.ts`: new pure
  `computeSeedProbabilities(model, picks): Map<string, number[]>` that reuses the `computePlayoffOdds`
  enumeration setup (baseWins with picks folded in, fixed points-for `tieRank`, `freeA`/`freeB`,
  exact-vs-Monte-Carlo branch) but accumulates each team's finishing rank into a per-seed histogram.
  `computePlayoffOdds` is refactored to derive from it (sum of top-`num_playoff_teams` seeds) — same
  output, existing tests unchanged.
- `frontend/src/features/playoff_race_predictor/playoff-race-predictor.tsx`: new
  `SeedProbabilityTable` component rendered between `StandingsTable` and `ClinchScenarios`; the seed
  matrix is computed once in `PredictorTool` and shared, and `StandingsTable`'s odds column is
  derived from it.
- Tests: `compute-projection.test.ts` unit coverage (distributions sum to ~1, a hand-checkable
  known-rank case, consistency with `computePlayoffOdds`), a jest-cucumber scenario for the table,
  and demo/replay coverage.
