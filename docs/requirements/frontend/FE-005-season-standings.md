# FE-005: Season Standings

## Description
The `/standings` page shows final standings for a selected season, plus season superlative
awards. Standings include record, win %, points for/against, vs-league record, an
**expected wins** figure, and a strength-of-schedule (SoS) rating. A season selector lets the
user switch between onboarded seasons.

The **expected wins** column is each team's average number of wins across every manager's
schedule in the regular season — the mean of that team's row in the Schedule-Swap Simulator
([FE-031](FE-031-schedule-swap-simulator.md)), i.e. the average of the win totals it would post
under each schedule (its own included). It is a schedule-independent estimate of how many games
a team "should" have won given its own weekly scores. Like SoS it is derived client-side from
the season's `MATCHUPS` and is best-effort: it shows `—` when matchups are unavailable (or a
team has no simulated regular-season games).

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
- Also hosts the **Schedule-Swap Simulator**
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
  renders with the SoS and expected-wins columns showing `—` (both are best-effort, not fatal).

## Acceptance Criteria
- [ ] `/standings` shows the selected season's standings: record, win %, PF, PA, vs-league
      record, expected wins, SoS, sorted by standing.
- [ ] Expected wins shows each team's average wins across every schedule (the mean of its
      schedule-swap row), or `—` when it cannot be computed.
- [ ] SoS shows each team's average opponent season win % (regular season only), or `—` when
      it cannot be computed.
- [ ] Season superlative awards for the selected season are displayed.
- [ ] The season selector lists all onboarded seasons and defaults to the latest.
- [ ] Records and win % correctly account for ties.
- [ ] In-progress seasons render without error.

## Sources
`src/features/season_standings/`, `src/features/season_select/`.
