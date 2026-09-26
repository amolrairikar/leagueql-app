# Design

## Context

See proposal.md — Why. All computation happens in
`frontend/src/features/playoff_race_predictor/compute-projection.ts`.
`buildPredictorModel` already partitions the full season's matchups into a fixed baseline
plus pickable weeks. `computeSeedProbabilities` is the shared core: it treats each unpicked
matchup as a free win/loss bit, enumerates all `2^N` combinations exactly when
`N ≤ MAX_EXACT_MATCHUPS` (20) and otherwise draws `MONTE_CARLO_SAMPLES` (50,000) via a seeded
`mulberry32` PRNG, tallying each team's finishing seed. `computePlayoffOdds` and the standings
odds column both derive from it, and `computeClinchScenarios` runs its own guarantee-based
enumeration. The frontend already receives every regular-season matchup with real scores
(`team_a_score` / `team_b_score`, typed `number`).

## Goals / Non-Goals

**Goals:**
- Weight each unpicked matchup by a win probability from the two teams' scoring distributions.
- Keep the change confined to `computeSeedProbabilities` plus scoring stats on the model, so
  odds, seed odds, and their consistency all follow automatically.
- Degrade to today's exact 50/50 behavior when scoring history is absent.

**Non-Goals:**
- Simulating actual points-for (it stays fixed as a tiebreaker).
- Changing clinching scenarios — guarantees are outcome-set membership, independent of how
  likely each outcome is, so that code and requirement are untouched.
- Opponent/strength-of-schedule adjustments or non-normal score models.

## Decisions

- **Win-probability bit model, not full score simulation.** Each matchup stays a single
  win/loss bit; only the weight of each outcome changes. This preserves exact enumeration (now
  a weighted sum), the seeded Monte-Carlo fallback, and leaves clinch logic and the fixed
  points-for tiebreak intact. Full score simulation would abandon exact enumeration and force
  a clinch-scenario rewrite for marginal benefit.
- **Normal approximation for win probability.** Treat each team's game score as `N(μ, σ)`,
  independent, so the margin is `N(μA − μB, √(σA² + σB²))` and
  `P(A beats B) = Φ((μA − μB)/σdiff)`. `Φ` uses an erf approximation (Abramowitz & Stegun
  7.1.26) — no dependency needed. `σdiff ≤ ε → 0.5`.
- **Per-team σ with league-wide fallback.** Use a team's own sample σ only when it has ≥ 3
  played games and a non-trivial spread; otherwise use the league-wide pooled within-team
  residual std. This avoids degenerate `σ = 0` (a 1-game team, or repeated identical scores)
  producing a 0/1 blowout. Per-team means are always used when the team has ≥ 1 game.
- **Compute scoring stats once, in `buildPredictorModel`.** Store a resolved
  `teamScoring?: Map<teamId, { mean; std; games }>` on the model (σ already fallback-resolved).
  `computeSeedProbabilities` reads it via a `matchupWinProb(model, a, b)` helper. The field is
  **optional** so the test helper `mkModel` and any model built with no played games leave it
  unset and the helper returns 0.5 — exactly today's behavior.
- **Weighting mechanics.** Precompute `pFree[b]` = P(freeA[b] wins) per free matchup. Exact
  path: each `mask` contributes `weight = ∏_b ((mask>>b)&1 ? 1 − pFree[b] : pFree[b])` (bit 0
  = freeA wins, matching the existing `wins[bit ? freeB : freeA]++` convention) to `seedCounts`
  instead of 1; normalize by accumulated total weight (analytically 1, divided for safety).
  Monte-Carlo path: draw `rand() < pFree[b] ? freeA[b] : freeB[b]`.

## Risks / Trade-offs

- **Small per-season samples make σ noisy.** → The ≥ 3-game threshold plus league-wide σ
  fallback keeps early-season estimates stable; means still personalize each team.
- **Normal model ignores score skew / correlation.** → Acceptable for a lightweight in-app
  estimate; the odds are directional guidance, not a betting line. Documented in the spec as a
  normal approximation.
- **Odds and clinch scenarios use different engines.** → They stay consistent because clinch
  guarantees are about whether a team is in/out across *all* outcomes; a guaranteed-in team has
  weighted odds of exactly 1 and a guaranteed-out team exactly 0 regardless of weighting.
- **Existing tests could shift.** → `mkModel` tests and no-score fixtures fall back to 50/50
  and stay green; the one played-score range assertion (`t1` odds ∈ (0.5,1)) holds because
  `t1` is the clear scoring leader. Verified by re-running the suite.
