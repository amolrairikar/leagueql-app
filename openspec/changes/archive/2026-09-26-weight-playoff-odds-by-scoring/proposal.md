# Proposal

## Why

The playoff-race predictor's playoff odds and per-seed probabilities treat every unpicked
remaining matchup as an equally likely 50/50 coin flip, ignoring how each team has actually
scored. A dominant scoring team beating a weak one is far more likely than a coin flip, so
the current odds under- and over-state real playoff chances. We already fetch every
regular-season matchup (with real scores) for the season, so a better estimate can be
computed entirely in the frontend with no new data or API.

## What Changes

- Replace the flat 50/50 weight for each unpicked matchup with a win probability derived from
  the two teams' season scoring distributions: `P(A beats B) = Φ((μA − μB) / √(σA² + σB²))`,
  using each team's regular-season scoring mean and standard deviation.
- Per-team standard deviation uses the team's own sample σ when it has ≥ 3 played games and a
  non-trivial σ; otherwise it falls back to a league-wide σ (pooled within-team residual std).
- When a team has no played games (or the league has no played games at all), the matchup
  falls back to an equal 50/50 weight, so an un-started season behaves exactly as today.
- Keep the win/loss-bit outcome model: exact enumeration of all `2^N` combinations when small
  enough (each combination now weighted by its probability) and seeded Monte-Carlo sampling
  above the threshold (each matchup drawn at its win probability). Points-for stays fixed and
  is used only to break ties.
- Playoff clinching scenarios are unchanged — they are guarantee-based (what is mathematically
  certain across all outcomes) and do not depend on how likely each outcome is.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/playoff-race-predictor`: the "Show each team's playoff odds" and "Show per-team
  playoff seed probabilities" requirements change how remaining unpicked matchups are weighted
  — from an equal 50/50 outcome to a win probability derived from the two teams' scoring
  distributions, with a 50/50 fallback when a team lacks scoring history. Exact-enumeration /
  sampling and the fixed points-for tiebreak are retained.

## Impact

- Frontend only. `frontend/src/features/playoff_race_predictor/compute-projection.ts`
  (`buildPredictorModel` gains per-team scoring stats; `computeSeedProbabilities` weights
  outcomes by matchup win probability). `computePlayoffOdds` and the standings odds column
  inherit the change automatically (both derive from `computeSeedProbabilities`).
- Unit tests in `compute-projection.test.ts` gain cases for favored teams, the no-history
  fallback, and weighted sampling determinism.
- No backend, API, DynamoDB, architecture, or extension changes. The clinching-scenarios
  requirement and its implementation are untouched.
