# FE-006: Matchups & Box Scores

## Description
The `/matchups` page browses every historical matchup. The user selects a season and week
to see all matchups for that week, and can open a matchup to view the full box score
(starters and bench with per-player points) for both teams.

## Scope
- Route: `/matchups` (protected, app layout).
- Component: `src/features/matchups/matchups.tsx`; API in `api-calls.ts`.
- Box score card: `src/components/box-score-card.tsx`.
- Reads `MATCHUPS#{season}#WEEK#{week}` via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).
- Hosts two gated premium sections below the matchup grid, in order: the **Weekly Awards &
  Superlatives** section ([FE-032](FE-032-weekly-awards-superlatives.md)), then the **AI Weekly
  Recap** section ([FE-033](FE-033-ai-weekly-recap.md)). Both reuse the page's season + week
  navigation and are wrapped in `SubscriptionGuard` (premium). Page order: matchup grid →
  FE-032 superlatives → FE-033 recap.

## Edge Cases
- **Playoff weeks:** matchups carry `playoff_tier_type`/`playoff_round`; display the round
  label for postseason games.
- **Bye / odd team count:** weeks where a team has no opponent are handled.
- **In-progress week:** scores may be incomplete/zero; render without error.
- **Missing player names/positions:** box score tolerates null player metadata.
- **Co-owned teams / missing logos:** fall back to avatars.
- **Season/week selector bounds:** week list reflects only weeks that exist for the season.

## Acceptance Criteria
- [ ] `/matchups` lets the user pick a season and week and lists all matchups for that week
      with team names, logos, scores, and winner.
- [ ] Opening a matchup shows both teams' starters and bench with per-player points.
- [ ] Playoff matchups display their round label.
- [ ] The week selector only offers weeks that exist for the chosen season.
- [ ] Incomplete/in-progress weeks and missing player metadata render gracefully.

## Sources
`src/features/matchups/`, `src/components/box-score-card.tsx`.
