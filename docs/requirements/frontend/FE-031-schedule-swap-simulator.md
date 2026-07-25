# FE-031: Schedule-Swap Simulator

## Description
A free section on the `/standings` page that answers the league's eternal "I'm unlucky"
argument: **"What would each team's record be if it had played another manager's schedule?"**

For the selected season it renders an N×N matrix computed entirely client-side from the
regular-season `MATCHUPS` view:
- **Rows** = each team's *own* weekly scores (held fixed).
- **Columns** = each manager's *schedule* (the sequence of opponents they faced).
- **Cell** `[row, col]` = the row team's win total if it had played the column manager's
  opponents each week, using its own actual scores.
- **Diagonal** (`row === col`) reproduces each team's **actual** record and is highlighted.

Cells are color-scaled by how the swapped win total compares to the team's actual wins:
greener = more wins than they actually got (a softer schedule), redder = fewer. A team
reading its own row at a glance sees whether it was schedule-lucky or schedule-unlucky.

## Scope
- Lives on the `/standings` page ([FE-005](FE-005-season-standings.md)), below the existing
  standings/awards/wins-progression sections, scoped to the page's season selector.
- Component: `src/features/schedule_swap/schedule-swap.tsx`; pure transform in
  `compute-schedule-swap.ts`; data fetch reuses `getSeasonMatchups`
  (`MATCHUPS#{season}#`, [BE-005](../backend/BE-005-query-precomputed-views-api.md)).
- **Free:** the section and its header always render for everyone.

## Swap algorithm
- Only **regular-season** matchups count (`playoff_tier_type` is `NONE`/absent); playoff and
  consolation games are excluded because they are not a round-robin schedule.
- For the row team `R` using column manager `C`'s schedule, iterate the weeks `C` actually
  played. Each week, `R`'s opponent is whoever `C` faced that week — **except** when `C`
  faced `R` itself, in which case `R` faces `C` (it takes `C`'s slot, never plays itself).
  Compare `R`'s actual score that week against the substituted opponent's actual score.
- Records are `W-L-T`; ties counted. The diagonal therefore equals the team's real record.

## Edge Cases
- **Season in progress:** the matrix reflects regular-season weeks played so far.
- **Byes / odd team counts:** a week where the row team or its substituted opponent has no
  score (a bye) is skipped, so swapped records can span fewer games than the diagonal.
- **Self-matchup substitution:** when the borrowed schedule would pit a team against itself,
  it faces the schedule's owner instead (see algorithm).
- **Fewer than two teams / no regular-season data:** show an empty-state message instead of
  an empty grid.
- **No `MATCHUPS` data (404) or load failure:** surface an inline message; never throw.
- **Many teams:** the grid scrolls horizontally; the first column (team) and header row
  (schedule owner) stay sticky.

## Acceptance Criteria
- [ ] On `/standings`, a Schedule-Swap matrix renders for the selected season with one row
      and one column per team.
- [ ] The diagonal cell for each team equals that team's actual regular-season record and is
      visually highlighted.
- [ ] An off-diagonal cell equals the row team's win total under the column manager's
      schedule, with the self-matchup substitution applied.
- [ ] Cells are color-scaled relative to the row team's actual wins (more = green, fewer =
      red).
- [ ] Switching the season selector recomputes the matrix.
- [ ] The section renders for everyone.
- [ ] A `MATCHUPS` load failure or fewer-than-two-teams season renders a message, not a crash.

## Sources
`src/features/schedule_swap/`, `src/features/season_standings/season-standings.tsx`.
