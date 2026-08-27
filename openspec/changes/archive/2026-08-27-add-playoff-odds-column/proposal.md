## Why

The playoff-race predictor shows a single deterministic projection from whatever winners the user has
picked, but it never answers the question managers actually care about: *what are a team's chances of
making the playoffs given everything that could still happen?* A team can be one game back with an easy
schedule and look worse in a hand-picked projection than a rival that is realistically in trouble. A
**playoff-odds** percentage — the share of all possible remaining outcomes in which a team finishes
inside the playoff cutoff — turns the tool from "here is one scenario" into "here is how likely you are
to make it."

## What Changes

- Add a **Playoff odds** column to the predictor's projected-standings table. For each team it shows the
  percentage of possible future outcomes in which the team lands in a top-`num_playoff_teams` seed.
- Odds treat every remaining **unpicked** regular-season matchup as an equally likely 50/50 coin flip, so
  every combination of results is weighted equally. Points-for is not simulated (it is only a tiebreaker
  and is already fixed), so each matchup is a pure binary win/loss and the outcome space is exactly `2^N`.
- Odds are **conditional on the user's current picks**: a pick locks that game in, and the column
  recomputes over the remaining unpicked matchups — in the base view (no picks) it reflects all outcomes.
- Odds are computed **exactly** by enumerating all `2^N` combinations when `N` (unpicked matchups) is
  small enough, and by **Monte Carlo sampling** when the outcome space is too large to enumerate. A
  clinched team reads 100% and an eliminated team 0%.

## Capabilities

### Modified Capabilities
- `frontend/playoff-race-predictor`: the projected-standings table gains a per-team playoff-odds
  percentage derived from all possible remaining outcomes (equal-weighted coin flips), conditional on the
  user's picks, computed exactly for small outcome spaces and by sampling for large ones.

## Impact

- Frontend only. No backend / API / DynamoDB / infrastructure / architecture-diagram change.
- `frontend/src/features/playoff_race_predictor/compute-projection.ts`: new pure `computePlayoffOdds`
  function (plus a small seeded PRNG for the deterministic sampling path), reusing the existing
  `compareRecords` seeding and top-`num_playoff_teams` cutoff.
- `frontend/src/features/playoff_race_predictor/playoff-race-predictor.tsx`: new column in the standings
  table (header, cell, formatting, cutoff-line `colSpan` bump, footer note).
- Tests: `compute-projection.test.ts` unit coverage for the odds math (coin-flip symmetry, clinched/
  eliminated, conditional-on-picks, deterministic sampling path) and a jest-cucumber scenario asserting
  the column renders a percentage and updates on a pick.
