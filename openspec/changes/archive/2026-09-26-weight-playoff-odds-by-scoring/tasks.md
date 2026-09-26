# Tasks

## 1. Scoring stats on the model

- [x] 1.1 Add optional `teamScoring?: Map<string, { mean: number; std: number; games: number }>` to `PredictorModel` in `compute-projection.ts`; verify the project type-checks (`cd frontend && npx tsc -b`).
- [x] 1.2 In `buildPredictorModel`, collect each team's scores from every played regular-season matchup (`isRegularSeason(m) && !isUnplayedMatchup(m)`), compute per-team mean, a league-wide pooled within-team residual σ, and a resolved per-team σ (own σ when games ≥ 3 and non-trivial, else league-wide), storing the result on `model.teamScoring`; verify with a unit test asserting the computed mean/games for a small played-games fixture.

## 2. Win-probability weighting

- [x] 2.1 Add internal helpers `normalCdf(z)` (erf approximation) and `matchupWinProb(model, aId, bId)` (returns 0.5 when scoring data is absent, a team has 0 games, or σdiff ≤ ε; else `Φ((μA−μB)/√(σA²+σB²))`); verify with a unit test that a clearly stronger mean yields > 0.5 and equal means yield 0.5.
- [x] 2.2 In `computeSeedProbabilities`, precompute `pFree[b]` per free matchup and weight the exact enumeration (`weight = ∏ (bit ? 1−pFree : pFree)`, normalized by accumulated total weight) and the Monte-Carlo draw (`rand() < pFree[b]`); update the doc comment away from the 50/50 wording. Verify the "distributions sum to 1" and "agrees with computePlayoffOdds" unit tests still pass.

## 3. Tests

- [x] 3.1 Add unit tests in `compute-projection.test.ts`: a favored team's playoff odds exceed 50% (weaker < 50%, sum preserved); no-scoring-history reverts to 50/50; a <3-game team uses the league σ fallback (favorite still emerges, no 0/1 blowout); weighted Monte-Carlo determinism over a >20-matchup space built with played scores. Run `cd frontend && npx vitest run src/features/playoff_race_predictor/__tests__/compute-projection.test.ts` — all green.
- [x] 3.2 Run the predictor UI steps suite `cd frontend && npx vitest run src/features/playoff_race_predictor/__tests__/playoff-race-predictor.steps.test.tsx` and confirm all scenarios still pass (structure / clinched extremes, unaffected by weighting).

## 4. Integration & housekeeping

- [x] 4.1 Run `cd frontend && npm run lint && npm run format:fix` — no lint errors, formatting clean.
- [x] 4.2 Run `openspec validate weight-playoff-odds-by-scoring --strict` — the change validates with no dangling references.
