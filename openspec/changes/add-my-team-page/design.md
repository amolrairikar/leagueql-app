# Design

## Context

See proposal.md for why. Everything the Your week card shows can already be computed on the
client from data other pages load:

- **Season matchups:** `getManagerHistoryData` returns every season's `MATCHUPS`, the per-season
  standings, and the platform-migration `migrationMapping`.
- **Matchup preview:** `buildMatchupPreview` (`features/matchups/compute-preview.ts`) gives the
  projected score and win probability.
- **Playoff odds:** `buildPredictorModel` + `computePlayoffOdds`
  (`features/playoff_race_predictor/compute-projection.ts`), plus `getLeagueSettings` for the
  number of playoff teams.
- **Lineup efficiency:** `computeStartSitReport` (`features/lineup_efficiency/`) per team-week.
- **Weekly awards:** `computeWeeklyAwards` (`features/weekly_awards/`).

The one new piece of state is *which team is mine*, which must persist per user, per league.

## Goals / Non-Goals

**Goals:**
- One small backend surface (`GET`/`PUT /me`) with the same auth and membership model as
  existing reads.
- Reuse the existing calculations unchanged, so My Team never disagrees with Matchups, the
  predictor, or the efficiency chip.
- Ship on for everyone. There is no feature flag, by decision.

**Non-Goals:**
- Verifying that the Clerk user really is the platform manager.
- Email digests. The row is a disabled placeholder.
- Any new precomputed view or processor change.

## Decisions

**1. Store the claim under the league's partition (`PK=LEAGUE#{canonical_id}`,
`SK=USER#{clerk_user_id}`).**
- Deleting a league already removes everything under its PK (`collect_league_keys`), so claims
  cascade for free.
- A future digest job can list a league's users with one `begins_with(SK, "USER#")` query.
- *Alternative:* `PK=USER#{clerk_user_id}, SK=LEAGUE#{id}`, like `ESPN_CREDENTIALS`. It is better
  for "all of a user's leagues", but it needs its own cleanup on league delete and has no current
  use case.

**2. Store the platform owner id, not the `team_id`.**
- `team_id` is per season and changes on a Sleeper renewal or a migration. `primary_owner_id`
  follows the manager.
- The page resolves the current team by matching
  `migrationMapping.get(id) ?? id` on both the stored id and each matchup's
  `team_{a,b}_primary_owner_id`. This is the same remapping Home's all-time standings use.
- Co-owners claim the team's primary owner, so they land on the right team.

**3. Validate `owner_id` against the league's `TEAMS` view (any season's `primary_owner_id`).**
- This prevents storing junk ids without adding platform calls.
- Any season is accepted (not just the current one), so a stale-but-real claim can still be
  saved. The frontend only offers current-season teams anyway.

**4. Membership gate identical to reads (`require_league_member`).**
- Sleeper stays open to any signed-in user. ESPN and Yahoo require the owner or a member.
- A claim only personalizes the claimer's own view, so an unverified claim is harmless.

**5. Route `/my_team` (snake_case).**
- This matches existing routes (`/playoff_bracket`, `/manager_history`) rather than the
  `/my-team` spelling used during planning.

**6. Playoff odds change = odds(now) − odds(as of before last week).**
- Build a second model from the same matchups with last week's regular-season games reset to
  0–0, so they count as unplayed. Those scores then also drop out of the scoring distributions.
- Call `computePlayoffOdds(model, {})` on both models.
- This is deterministic: exact at ≤20 unpicked games, otherwise a seeded 50k-sample Monte Carlo
  (about ±0.2 pts).
- The change is hidden in Week 1, and once the regular season is over (no reg-season week to
  roll back).

**7. Season efficiency = Σ actual ÷ Σ optimal across played regular-season weeks with lineup
data.**
- This is a points-weighted ratio, not an average of weekly percentages, so a low-scoring week
  doesn't count the same as a high one.
- Last week's bench points come from the same per-week report.

**8. "Current week" / "last week".**
- The current season is the latest season.
- The current week is the lowest week with any unplayed (0–0) matchup in the league. It is
  league-wide rather than the claimed team's next game, so a bye week shows "No matchup this
  week" instead of being skipped.
- Last week is the highest fully played week below it.
- If no unplayed matchups remain, the season is in the offseason view.

**9. No feature flag.**
- The page and its sidebar entry are always on. The backend and infrastructure (CORS `PUT`, the
  `/me` routes) must deploy before the frontend, because the page calls `/me` as soon as it
  ships.

**10. Demo mode.**
- `lib/demo-api.ts` answers `GET /me` with the first demo owner and ignores `PUT`. The page keeps
  the selection in component state.

## Risks / Trade-offs

- **[Two predictor runs per page load could be slow on a large league with many games left]**
  → Both are capped by the existing exact/Monte-Carlo switch. Compute them in `useMemo`, keyed on
  the matchups, so each runs once per load.
- **[The `0–0` = unplayed convention also matches a real 0–0 tie]** → This is the existing
  app-wide convention (`isUnplayedMatchup`), so it is accepted here too.
- **[Rank uses wins, then points for, so it may differ from platform tiebreakers]** → This matches
  the predictor's projected standings, and "rank" is labeled simply. Revisit if the stored
  STANDINGS view gains platform ranks mid-season.
- **[Unverified claims on open Sleeper leagues]** → Personal view only; documented in the spec
  and here.

## Migration Plan

1. Deploy the backend: the new endpoints, and `openapi_spec.yaml` routes via the API Gateway
   Terraform.
2. Deploy the frontend. The page goes live immediately.
3. Rollback: revert the frontend deploy. Stored `USER#` items are inert.
