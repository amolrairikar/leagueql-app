# FE-008: Playoff Bracket

## Description
The `/playoff_bracket` page renders the winners'-bracket playoff tree for a selected season,
including seeding, per-round matchups with scores, and final placements (champion, runner-up,
etc.). Scores are joined from the matchups views; seeding lines are derived from each match's
`team_*_from` references.

## Scope
- Route: `/playoff_bracket` (protected, app layout).
- Component: `src/features/playoff_bracket/playoff-bracket.tsx`; API in `api-calls.ts`.
- Reads `PLAYOFF_BRACKET#{season}`, `MATCHUPS`, and `WEEKLY_STANDINGS` via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Edge Cases
- **Variable championship week:** championship week derived from actual matchup data
  (handles week 17 vs. 18, etc.).
- **Unplayed matches:** `winner`/`loser` null until played; render as TBD.
- **Seeding refs:** `team_*_from` (e.g. `{"w":1}`/`{"l":2}`) parsed to draw advancement lines.
- **Score matching:** bracket matches joined to matchups handling either team order.
- **No bracket / season in progress:** render a clear empty/partial state.
- **End-of-regular-season seeds:** derived from the last `WEEKLY_STANDINGS` snapshot week.
- **Missing logos:** fall back to a team-ID–derived color/avatar.

## Acceptance Criteria
- [ ] `/playoff_bracket` renders the bracket for the selected season with rounds, seeds,
      matchup scores, and final placements.
- [ ] Advancement lines reflect `team_*_from` seeding references.
- [ ] The championship week is derived from real matchup data, not hard-coded.
- [ ] Unplayed/in-progress matches render as TBD without error.
- [ ] Scores are correctly matched regardless of team order in the source data.

## Sources
`src/features/playoff_bracket/`.
