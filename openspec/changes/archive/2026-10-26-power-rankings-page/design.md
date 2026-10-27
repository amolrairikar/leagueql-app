# Design

## Context

`getSeasonMatchups(leagueId, platform, season)` returns every matchup of a season with scores and
`starters`/`bench` lists. That is enough to derive all four ranking inputs, and the repo already has
pure helpers for two of them: `computeStartSitReport` (optimal lineup, hence efficiency) and
`computeScheduleSwap` (expected wins from the schedule-swap matrix, used for the expected record shown in a team's breakdown but not in the score).

## Decisions

### Rankings are a pure function of the matchups, per "cut" week
`buildPowerRankings(matchups)` returns the played regular-season weeks and, for every cut `k`
(games through week `k`), the ranked rows. The page's "Week N" is cut `N - 1`. Computing all cuts up
front, in one memo keyed on the season's matchups, gives previous-week rank (cut `k - 1`) and the
six-week trend (cuts `k - 5 … k`) without extra state. A league has ~14 weeks and 12 teams, so the
cost is trivial.

Only regular-season, played games count (`isRegularSeasonMatchup`, not `isUnplayedMatchup`), matching
the other analytics pages. Playoff games would distort form and record for teams still alive.

### Components and scaling
| Component | Raw value | Scaling |
|---|---|---|
| Record | win % (ties count half) | `win% × 100` (absolute) |
| Points scored | total points for | min–max across teams |
| Recent form | mean score of the last 3 played weeks | min–max across teams |
| Lineup efficiency | Σ actual ÷ Σ optimal over weeks with bench data | min–max across teams |

Min–max scaling puts the best team at 100 and the worst at 0; when every team is
equal the component is 50 for all. Record stays absolute so a 7–0 team scores 100 regardless of how
the league is distributed. Weights are fixed constants (35/30/20/15).

### Missing components degrade instead of failing
Lineup efficiency needs bench data, which some seasons lack (for example ESPN seasons before 2018).
If no team has any, the component is shown as unavailable and the power score is the weighted average
of the remaining components, with weights renormalized. A team missing only some weeks is scored on
the weeks it has.

### Movement, trend and "record rank"
- Movement is previous rank − current rank, where the previous rank is the same fixed formula applied
  at cut `k − 1`. The first available week has no previous rank and shows no movement.
- Trend is the rank at up to the last six cuts, oldest first.
- Record rank orders teams by wins (ties as half a win), then points for. The gap to power rank
  labels a team Underrated (≥ 2 places better in power), Overrated (≥ 2 worse), or On the mark.

### Page structure
Follows the existing analytics pages: `getLeagueCookies()` for league and seasons, `SeasonSelect`,
`seasonQuery` + `use()` under `Suspense` with a skeleton, and `ErrorAlert` for load failures. The
week picker is a previous/next stepper over the available weeks. Rows expand to show the breakdown.
The lazy route and sidebar entry follow the route-code-splitting pattern.

## Risks / Trade-offs

- **In-progress weeks.** A week is counted as played once any score is non-zero, the same convention
  as the other pages, so a partially scored live week could count early.
- **Small samples.** Early-season rankings are noisy by nature. Week 2 rankings rest on one game.
