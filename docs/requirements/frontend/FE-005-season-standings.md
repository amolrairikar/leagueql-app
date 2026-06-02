# FE-005: Season Standings

## Description
The `/standings` page shows final standings for a selected season, plus season superlative
awards. Standings include record, win %, points for/against, and vs-league record. A season
selector lets the user switch between onboarded seasons.

## Scope
- Route: `/standings` (protected, app layout).
- Component: `src/features/season_standings/season-standings.tsx`; API in `api-calls.ts`.
- Season selector: `src/features/season_select/season-select.tsx`.
- Reads `STANDINGS#{season}` (and supporting views) via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Edge Cases
- **Season in progress:** standings reflect games played so far; superlatives may be partial.
- **Ties:** records show ties (`W-L-T`); win % computed with ties.
- **Default season:** defaults to the most recent onboarded season.
- **vs-league record:** reflects beating/losing to all teams each week, distinct from
  head-to-head record.
- **Missing logos:** fall back to generated avatars.

## Acceptance Criteria
- [ ] `/standings` shows the selected season's standings: record, win %, PF, PA, vs-league
      record, sorted by standing.
- [ ] Season superlative awards for the selected season are displayed.
- [ ] The season selector lists all onboarded seasons and defaults to the latest.
- [ ] Records and win % correctly account for ties.
- [ ] In-progress seasons render without error.

## Sources
`src/features/season_standings/`, `src/features/season_select/`.
