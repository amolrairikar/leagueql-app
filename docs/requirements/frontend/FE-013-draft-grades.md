# FE-013: Draft Grades

## Description
The `/draft_grades` page grades each manager's draft for a selected season and highlights
steals and busts using the precomputed `draft_rank_delta` (drafted position rank vs. actual
end-of-season position rank). Steals are players who massively outperformed their draft slot;
busts are early picks who badly underperformed.

## Scope
- Route: `/draft_grades` (protected, app layout).
- Component: `src/features/draft_grades/draft-grades.tsx`; API in `api-calls.ts`.
- Thresholds: `STEAL_DELTA_MIN = 5`, `BUST_DELTA_MAX = -5`, `BUST_ROUND_BUFFER = 4`,
  `BUST_ROUND_MAX = 10`.
- Reads `DRAFT#{season}` (with `draft_rank_delta`, `vorp`, ranks) via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Edge Cases
- **Steal classification:** `draft_rank_delta >= 5` → steal.
- **Bust classification:** `draft_rank_delta <= -5` AND picked more than `BUST_ROUND_BUFFER`
  rounds before the last round; only flag busts (and show alternatives) for rounds 1–10.
- **Null analytics:** picks with null `actual_position_rank`/`draft_rank_delta` (e.g. missing
  stats) are excluded from steal/bust flags.
- **K and D/ST:** `vorp` is null for these; grading must not error on nulls.
- **In-progress season:** end-of-season ranks may be incomplete; grades should be presented
  as provisional or handled gracefully.
- **Per-manager grade:** an overall grade is derived per manager from their picks.

## Acceptance Criteria
- [ ] `/draft_grades` assigns each manager a draft grade for the selected season.
- [ ] Steals (`delta >= 5`) and busts (`delta <= -5`, beyond the round buffer, rounds 1–10)
      are highlighted.
- [ ] Picks with null rank/delta are excluded from steal/bust flags.
- [ ] Grading handles null `vorp` for K/D/ST without error.
- [ ] In-progress seasons render without crashing.

## Sources
`src/features/draft_grades/`.
