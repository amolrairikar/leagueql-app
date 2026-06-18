# FE-005: Season Standings

## Description
The `/standings` page shows final standings for a selected season, plus season superlative
awards. Standings include record, win %, points for/against, vs-league record, and a
strength-of-schedule (SoS) rating. A season selector lets the user switch between onboarded
seasons.

The **strength-of-schedule** column is each team's average opponent season win % over the
regular season (higher = a tougher schedule). It is derived client-side from the season's
`MATCHUPS` (who each team faced) and the standings win % of those opponents — there is no
stored SoS field; playoff games are excluded to match how win % is computed.

## Scope
- Route: `/standings` (protected, app layout).
- Component: `src/features/season_standings/season-standings.tsx`; API in `api-calls.ts`.
  SoS computed by `src/features/season_standings/compute-sos.ts`.
- Season selector: `src/features/season_select/season-select.tsx`.
- Reads `STANDINGS#{season}` and `MATCHUPS#{season}#…` (and supporting views) via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).
- Also hosts the premium **Schedule-Swap Simulator**
  ([FE-031](FE-031-schedule-swap-simulator.md)), scoped to the same season selector.

## Edge Cases
- **Season in progress:** standings reflect games played so far; superlatives may be partial.
- **Ties:** records show ties (`W-L-T`); win % computed with ties.
- **Default season:** defaults to the most recent onboarded season.
- **vs-league record:** reflects beating/losing to all teams each week, distinct from
  head-to-head record.
- **Missing logos:** fall back to generated avatars.
- **SoS with no opponents:** a team with no regular-season opponents (or whose opponents are
  absent from the standings) shows `—`.
- **Matchups unavailable:** if the `MATCHUPS` query fails while standings load, the table still
  renders with the SoS column showing `—` (SoS is best-effort, not fatal).

## Acceptance Criteria
- [ ] `/standings` shows the selected season's standings: record, win %, PF, PA, vs-league
      record, SoS, sorted by standing.
- [ ] SoS shows each team's average opponent season win % (regular season only), or `—` when
      it cannot be computed.
- [ ] Season superlative awards for the selected season are displayed.
- [ ] The season selector lists all onboarded seasons and defaults to the latest.
- [ ] Records and win % correctly account for ties.
- [ ] In-progress seasons render without error.

## Sources
`src/features/season_standings/`, `src/features/season_select/`.
