# FE-032: Weekly Awards & Superlatives

## Description
A premium section on the `/matchups` page that auto-generates a per-week "awards reel" plus a
running, week-to-date tally of how many awards each manager has collected. It answers the
weekly water-cooler questions — who lit up the scoreboard, who got blown out, who backed into
an ugly win — without any manual bookkeeping.

Everything is computed **entirely client-side** from the season's `MATCHUPS` view (the same
data the Matchups page already fetches), so there is no backend, no new DynamoDB view, and no
API change. It mirrors the Schedule-Swap Simulator ([FE-031](FE-031-schedule-swap-simulator.md))
pattern: a pure transform of an existing precomputed view, gated behind `SubscriptionGuard`.

The section lives on `/matchups` and tracks the page's existing week navigation — there is no
separate week selector. The award cards reflect the **selected week**; the tally accumulates
across weeks `1 … selectedWeek`.

## Award definitions (per week, all derived from `MATCHUPS`)
- **Highest Score** — team with the maximum single-team score that week.
- **Lowest Score** — team with the minimum single-team score that week.
- **Biggest Blowout** — matchup with the largest winning margin (awarded to the winner).
- **Narrowest Win** — matchup with the smallest positive margin (awarded to the winner).
- **Best Loss** — the losing team with the highest score that week.
- **Worst Win** — the winning team with the lowest score that week.
- **Longest Active Streak** — surfaced in the cumulative section (not as a weekly card): the
  manager on the longest current win streak (length ≥ 2) as of the selected week, derived from
  per-week win/loss ordered by week.

**Tie-breaking** is deterministic, mirroring the sort tiebreak in
`compute-schedule-swap.ts`: compare the relevant score (higher/lower per award), then
`ownerUsername.localeCompare`. For margin-based awards (blowout/narrowest) ties break on margin,
then the winner's score, then the winner's username.

## Scope
- Lives on the `/matchups` page ([FE-006](FE-006-matchups.md)), below the matchup grid, scoped
  to the page's season + week navigation.
- Component: `src/features/weekly_awards/weekly-awards.tsx`; pure transform in
  `compute-awards.ts`; data fetch reuses `getSeasonMatchups` (`MATCHUPS#{season}#`,
  [BE-005](../backend/BE-005-query-precomputed-views-api.md)).
- **Premium-gated:** wrapped in `SubscriptionGuard` with the shared `premium_feature` flag
  ([FE-021](FE-021-subscription-access-control.md) / [FE-026](FE-026-feature-flags.md)). While
  `billing` is off the whole section — its header and the gated content — is **hidden**; with
  `billing` on but `premium_feature` off the guard is a pass-through and the section renders for
  everyone. When gated and the subscription is expired/absent, the guard renders a blurred lock
  overlay in place of the awards and the `WeeklyAwards` component is **not mounted**, so its
  `MATCHUPS` data is never fetched while locked. The section header is gated on
  `isBillingEnabled` so it disappears with the section when `billing` is off.

## Week scope
Awards are computed for **every week present in `MATCHUPS`** — both regular season and playoffs
— so each navigable week shows its awards (whoever played that week is eligible). Playoff weeks
are intentionally kept: managers are still competing (and chasing superlatives) right up until
they are eliminated. The week-to-date tally accumulates per-award-type counts across the weeks
`1 … selectedWeek`.

The tally **does not** show a combined total per manager: the awards mix desirable (highest
score) and undesirable (lowest score, worst win) outcomes, so summing them would be misleading.
Rows are sorted alphabetically by manager name.

## Edge Cases
- **Byes / odd team counts:** a matchup where a side has no valid score is skipped, and a
  self-matchup placeholder (`team_a_id === team_b_id`) is ignored, so byes never produce an award.
- **Tied matchup:** a tie (equal scores) has no winner/loser, so it is excluded from blowout,
  narrowest win, best loss, and worst win — but both teams still compete for highest/lowest score.
- **Playoff weeks:** awards are computed for postseason weeks too (only the teams that played
  that week are eligible).
- **Season in progress:** the tally reflects only the weeks played so far through the selected
  week; the streak is the current (trailing) run of wins as of that week.
- **No award computable for a type** (e.g. every game tied): that card shows an em dash and "No
  award this week" rather than a blank.
- **No `MATCHUPS` data (404) or load failure:** surface an inline message; never throw.
- **No matchup data at all:** show an empty-state message instead of an empty grid/table.
- **Locked (expired subscription):** the gated component is not mounted and never fetches.

## Acceptance Criteria
- [ ] On `/matchups`, a Weekly Awards section renders below the matchup grid for the selected
      season, showing one card per award type for the **selected week**.
- [ ] Navigating to a different week recomputes the award cards for that week.
- [ ] A week-to-date tally table lists each manager with a per-award-type count (no combined
      total), accumulated across weeks `1 … selectedWeek`, sorted alphabetically by manager.
- [ ] The longest active win streak holder (length ≥ 2) through the selected week is surfaced
      in the tally section.
- [ ] Ties, byes, and self-matchup placeholders are excluded as described; an award with no
      eligible winner shows a placeholder card.
- [ ] When `premium_feature` (and `billing`) is enabled and the league subscription is
      expired/absent, the section shows a blurred lock overlay instead of the awards and **does
      not fetch** the `MATCHUPS` data. With `billing` off the section and its header are hidden;
      with `billing` on but `premium_feature` off it renders for everyone.
- [ ] A `MATCHUPS` load failure renders an inline message, and a season with no matchup data
      renders an empty-state message — neither crashes.

## Sources
`src/features/weekly_awards/`, `src/features/matchups/matchups.tsx`,
`src/features/season_standings/season-standings.tsx` (awards-card markup),
`src/features/subscription/subscription-guard.tsx`,
`src/features/subscription/subscription-required.tsx` (blurred lock overlay).
