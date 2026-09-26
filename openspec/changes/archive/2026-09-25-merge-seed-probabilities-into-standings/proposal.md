## Why

The playoff-race predictor now has two adjacent tables keyed by the same team rows: the projected
standings (with a make/miss **Playoff odds** column) and a separate **Seed probabilities** table.
Reading a team's outlook means bouncing between them. Folding the per-seed columns into the standings
table puts a team's record, playoff odds, and full seed breakdown on one line — and lets us drop the
low-value **Win %** column to make room.

## What Changes

- Remove the standalone **Seed probabilities** table; move its per-seed columns into the
  projected-standings table (one column per playoff seed `1..num_playoff_teams`, appended after the
  existing columns).
- Remove the **Win %** column from the projected-standings table.
- Drop the **Miss** column: the standings already show the aggregate **Playoff odds**, so the per-seed
  columns simply break that number down — for each team, seeds `1..num_playoff_teams` sum to its
  playoff-odds percentage. The Playoff-odds column stays as the at-a-glance summary.
- Each seed cell keeps the plain-number style (reusing the `<1%` / `>99%` / integer-% formatting), with
  each team's most-likely seed emphasized and sub-1% values muted.
- No change to the computation model: the per-seed probabilities are still the same
  `computeSeedProbabilities` distribution over the un-picked outcomes; the playoff-odds column still
  equals the sum of a team's top-`num_playoff_teams` seed probabilities.

## Capabilities

### Modified Capabilities
- `frontend/playoff-race-predictor`: the per-team seed probabilities move from a separate table into
  the projected-standings table as per-seed columns (no Miss column; they sum to the Playoff-odds
  column), and the standings table drops its Win % column.

## Impact

- **Frontend only.** No backend / API / DynamoDB / infrastructure / architecture-diagram change.
- `frontend/src/features/playoff_race_predictor/playoff-race-predictor.tsx`: merge
  `SeedProbabilityTable` into `StandingsTable` (append seed columns, drop Win %, update the playoff-line
  divider `colSpan` and the table `minWidth`); remove the standalone `SeedProbabilityTable` /
  `SeedProbabilityRow` components and their render slot in `PredictorTool`.
- `frontend/src/features/playoff_race_predictor/compute-projection.ts`: unchanged
  (`computeSeedProbabilities` / `computePlayoffOdds` stay as-is).
- Tests: update the component + demo-mode scenarios that asserted the separate "Seed probabilities"
  section to assert the merged columns instead; unit tests unchanged.
