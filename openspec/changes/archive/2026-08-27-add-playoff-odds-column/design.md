## Context

The predictor's projection engine (`compute-projection.ts`) already computes seeding deterministically
from picks: `projectStandings` applies picked results to the baseline, sorts with `compareRecords`
(wins desc → points-for desc → team id) and marks the top `num_playoff_teams` as making the playoffs.
Playoff odds ask the same seeding question across *every* possible outcome of the remaining unpicked
matchups, so the seeding rule is reused unchanged; only the driver (enumerate/sample outcomes vs. read
the user's picks) is new.

## Key decisions

- **Equal-weight coin flips.** Each remaining unpicked matchup is a 50/50 binary, so every combination of
  outcomes is equally likely. This matches the user's intent ("all possible permutations/combinations")
  and needs no team-strength model.
- **Points-for is not simulated.** It is a tiebreaker only and is fixed at its season-to-date value, so a
  matchup contributes exactly one bit (which team wins). The outcome space is therefore exactly `2^N` for
  `N` unpicked matchups, and per-scenario seeding is fully determined by the win vector.
- **Conditional on picks.** Picked matchups are locked (they are part of the fixed base, like already-
  played games); odds enumerate/sample only the unpicked matchups. The base view enumerates all of them.
- **Exact when feasible, sampled otherwise.** With a ~12-team max (6 matchups/week), the realistic race
  window — the last ~3 weeks (`2^18 ≈ 262k`) — enumerates exactly and instantly. Deeper windows explode
  (`2^24+`), so above a scenario cap the engine falls back to Monte Carlo. Sampling uses a **seeded PRNG**
  (mulberry32) so the output is deterministic and unit-testable, and its approximation error (±~1%) only
  applies early in the season when odds are near-uniform anyway.
- **Separate from `projectStandings`.** The odds calc is threaded into the table like `gamesLeft` (its own
  memo, looked up per row) rather than folded into `projectStandings`, keeping the cheap deterministic
  projection decoupled from the heavier odds computation.

## Edge cases

- `N === 0` (nothing left unpicked): odds are 100% for teams in the projected top-N, 0% otherwise.
- Clinched teams resolve to 100% and eliminated teams to 0% naturally from the enumeration.
- Odds are hidden (rendered as `—`) only if a case ever exceeds both the exact cap and the sampling path;
  in practice the sampling fallback always yields a number.
