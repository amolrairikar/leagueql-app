# FE-011: Matchup Records

## Description
The `/matchup_records` page surfaces all-time team/matchup superlatives across league
history: Highest Team Score, Lowest Team Score, Highest Matchup Score (combined), Lowest
Matchup Score, Biggest Blowout (largest margin), and Closest Game (smallest margin).

## Scope
- Route: `/matchup_records` (protected, app layout).
- Component: `src/features/matchup_records/matchup-records.tsx`; API in `api-calls.ts`.
- Reads all `MATCHUPS` items via [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Record Categories
- Highest Team Score — single team's highest score.
- Lowest Team Score — single team's lowest score.
- Highest Matchup Score — highest combined two-team total.
- Lowest Matchup Score — lowest combined two-team total.
- Biggest Blowout — largest point margin.
- Closest Game — smallest point margin.

## Edge Cases
- **Ties (margin 0):** "Closest Game" handles a zero margin.
- **In-progress / zero-score weeks:** incomplete matchups should not pollute records (e.g.
  exclude unplayed games).
- **Playoff vs. regular season:** define whether records span all games or regular season
  only — and apply consistently.
- **Each record links to context:** owner/team, season, and week of the record.

## Acceptance Criteria
- [ ] `/matchup_records` shows all six record categories with the team(s), season, and week.
- [ ] Highest/lowest team scores and matchup (combined) scores are computed correctly.
- [ ] Biggest blowout and closest game use point margin, with ties handled.
- [ ] Unplayed/in-progress matchups do not produce false records.

## Sources
`src/features/matchup_records/`.
