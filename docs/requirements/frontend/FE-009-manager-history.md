# FE-009: Manager History

## Description
The `/manager_history` page shows the year-to-year performance arc of each manager: per-season
records and finishes, plus a rivalry tracker that classifies each opponent relationship as a
domination, nemesis, or even rivalry based on head-to-head win rate.

## Scope
- Route: `/manager_history` (protected, app layout).
- Component: `src/features/manager_history/manager-history.tsx`; API in `api-calls.ts`.
- Rivalry thresholds: `DOMINATION_WIN_RATE = 0.65`, `NEMESIS_WIN_RATE = 0.40`.
- Builds per-owner per-season schedules including postseason (winners, losers, consolation
  brackets); reads matchups/standings/teams/bracket via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Edge Cases
- **Rivalry classification:** win rate ≥ 0.65 → domination; < 0.40 → nemesis; otherwise even.
- **Small sample rivalries:** few head-to-head games can skew the classification; handle so
  a 1-game "rivalry" isn't misleading.
- **Postseason inclusion:** schedule includes winners/losers/consolation bracket games.
- **Migrated league:** identities remapped across platforms.
- **New manager (one season):** history and rivalries render with limited data.
- **Manager selection:** defaults to a sensible manager; switching is supported.

## Acceptance Criteria
- [ ] `/manager_history` shows the selected manager's per-season records/finishes.
- [ ] A rivalry tracker classifies opponents as domination / nemesis / even using the win-rate
      thresholds.
- [ ] Postseason games are included in the schedule used for records/rivalries.
- [ ] Identities are correct across migrated platforms.
- [ ] Renders for a manager with only one season of history.

## Sources
`src/features/manager_history/`.
