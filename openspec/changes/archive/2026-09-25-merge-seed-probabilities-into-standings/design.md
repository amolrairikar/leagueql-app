## Context

The per-seed distribution (`computeSeedProbabilities`) and the aggregate playoff odds
(`computePlayoffOdds`, the sum of a team's top-`num_playoff_teams` seed probabilities) already share
one enumeration, computed once in `PredictorTool` and passed to both tables. This change is a pure
presentation refactor: the seed columns move into the standings table and the redundant Win % / Miss
columns go away. No math changes.

## Key decisions

- **One table.** `StandingsTable` gains a column per playoff seed `1..num_playoff_teams`, appended
  after `Games left`. The standalone `SeedProbabilityTable`/`SeedProbabilityRow` are deleted along with
  their slot in `PredictorTool`; `seedProbs` is now consumed only by `StandingsTable` (still computed
  once and passed in).
- **Drop Win %.** Removed from the header and each row. It was display-only (never spec'd) and low
  value next to the record and odds.
- **Drop Miss; odds is the row-sum.** With the aggregate Playoff-odds column present, a Miss column
  would be redundant (`Miss = 100% − odds`) and the seed columns already sum to the odds. So the
  per-seed columns show only seeds `1..num_playoff_teams`; the invariant `sum(seed 1..N) = playoff odds`
  is the visible relationship.
- **Most-likely emphasis.** Bold each team's highest per-seed cell among the shown seed columns (its
  most likely *playoff seed*); mute `<1%`; `tabular-nums` throughout — same treatment the standalone
  table used, minus the Miss bucket.
- **Layout mechanics.** The playoff-line divider row's `colSpan` becomes `5 + num_playoff_teams`
  (Seed·Owner, Proj. record, Playoff odds, PF, Games left, then N seed columns). The table `minWidth`
  grows with the seed-column count so the row stays scannable inside the existing `overflow-x-auto`
  wrapper. A subtle left border on the first seed column separates the standings meta from the seed
  breakdown.

## Edge cases

- **Large outcome space.** Seed cells still come from the sampled distribution (unchanged), so the
  merged columns render with sampled percentages just like the odds column.
- **Assumed playoff-team count.** The existing "Top N make the playoffs (assumed)" caption on the
  standings header already covers the assumed case; no separate caveat is needed now that there is one
  table.
