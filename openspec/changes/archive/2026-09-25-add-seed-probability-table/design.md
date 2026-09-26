## Context

`compute-projection.ts` already enumerates every combination of the remaining **un-picked** matchups
to compute playoff odds (`computePlayoffOdds`, exact when `≤ MAX_EXACT_MATCHUPS`, else 50k-sample
Monte Carlo). Inside `tallyScenario` it computes, for each team, `above` = the number of teams that
outrank it in that combination (wins desc, then fixed points-for `tieRank`) — i.e. its exact
finishing rank — but only keeps the boolean `above < num_playoff_teams`. The seed-probability table
asks for the full distribution of `above`, so it reuses the identical enumeration and seeding and
just accumulates a histogram instead of a single counter.

## Key decisions

- **One enumeration, two views.** `computeSeedProbabilities` becomes the enumeration core; each team
  gets a length-`n` array where index `k` is the probability of finishing rank `k+1` (seed `k+1`).
  `computePlayoffOdds` is refactored to call it and sum indices `0..num_playoff_teams-1` — byte-for-
  byte the same output it produces today, so its unit tests are untouched. `PredictorTool` computes
  the matrix once in a `useMemo` and passes it to both the standings table (for its odds column) and
  the new table, replacing the standings table's own `computePlayoffOdds` call.
- **Columns = playoff seeds + Miss.** The table shows one column per seed `1..num_playoff_teams` plus
  a **Miss** column = the summed probability of ranks `num_playoff_teams..n-1`. Each row therefore
  sums to ~100%, matching the "probability of each playoff seed" framing without a very wide
  full-standings matrix.
- **Distributions are proper.** In the exact path every enumerated combination assigns each team a
  unique rank (wins broken by the fixed `tieRank`), so each team's histogram sums to exactly the
  scenario count and the normalized array sums to exactly 1. In the Monte-Carlo path it sums to ~1,
  the same approximation the odds column already tolerates.
- **Plain-number cells.** No heat tint. Cells reuse the existing `formatOdds` helper (`0%` / `100%` /
  `<1%` / `>99%` / integer %). Each team's most-likely bucket (argmax over the `num_playoff_teams`
  seed values and the aggregated Miss value) is bold; sub-1% cells are muted (`text-muted-foreground`);
  everything is `tabular-nums`. Row order reuses `projectStandings(model, picks)` so the seed table's
  rows line up with the standings above it.
- **Conditional on picks.** Like the odds column, the matrix enumerates only the **un-picked**
  matchups (picks fold into the fixed base), so it recomputes on every pick/reset via the shared
  `useMemo`.
- **Demo (replay) mode included.** The table lives in the shared `PredictorTool`, which drives both
  `live` and `replay` modes, so demo mode renders it with no extra wiring; the demo dataset supplies
  real `LEAGUE_SETTINGS` and scored `MATCHUPS`.

## Edge cases

- **Large outcome space.** When `numFree > MAX_EXACT_MATCHUPS` the matrix is estimated by the same
  Monte-Carlo sampling as the odds — the table is still shown (unlike clinching scenarios, which need
  exact guarantees), with sampled percentages.
- **Assumed playoff-team count.** When `num_playoff_teams` was defaulted (platform omitted it), the
  table carries the same "(assumed)" caveat the standings/clinching sections use.
- **Fewer teams than the theoretical column set.** Columns are bounded by `num_playoff_teams`; the
  Miss column collapses all non-playoff ranks, so leagues of any size render a fixed-width, readable
  table.
