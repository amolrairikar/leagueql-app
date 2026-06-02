# FE-010: Player Records

## Description
The `/player_records` page surfaces all-time fantasy player performance records across the
league's history — e.g. the best single-game scoring performances by position, derived from
the per-player points recorded in matchup box scores.

## Scope
- Route: `/player_records` (protected, app layout).
- Component: `src/features/player_records/player-records.tsx`; API in `api-calls.ts`.
- Position set/colors: `src/lib/position-constants.ts`.
- Reads matchup starter/bench player stats via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Edge Cases
- **Missing points (`points_scored == null`):** such player-rows are skipped, not counted.
- **Position filtering:** only recognized positions (`POS_SET`) are included.
- **Players on multiple teams/seasons:** records attributed to the correct team/owner/season
  context of the performance.
- **Defenses/kickers:** positions like D/ST and K are handled per the position set.
- **Ties in record values:** consistent tie-breaking / display.

## Acceptance Criteria
- [ ] `/player_records` lists all-time player performance records by position.
- [ ] Player-rows without a recorded score are excluded.
- [ ] Only recognized positions are shown.
- [ ] Each record shows player, position, points, and the owner/season context.

## Sources
`src/features/player_records/`, `src/lib/position-constants.ts`.
