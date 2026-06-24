# FE-036: Positional Scoring Breakdown (Analytics)

## Description
A third chart on the premium **Analytics** page (`/analytics`), shown under the header
**"Positional Scoring"**: a **stacked horizontal bar chart**, one bar per manager, of each
manager's **total starter points for the selected season split by position**. Bar length is the
manager's total starter points and each colored segment is one position's contribution, so
roster construction reads at a glance — who is carried by their RBs, whose QB slot is a
sinkhole, who is balanced.

Everything is computed **entirely client-side** from the season's `MATCHUPS` view (the same data
the Score Distribution and Power Rankings charts already fetch), so there is no backend, no new
DynamoDB view, and no API change. It mirrors the Score Distribution
([FE-033](FE-033-score-distribution-analytics.md)) and Power Rankings
([FE-034](FE-034-power-rankings-trend.md)) pattern: a pure transform of an existing precomputed
view, gated behind `SubscriptionGuard`. It renders as a **third stacked section** below the power
rankings chart on the same Analytics page, under its own `SubscriptionGuard`, driven by the same
page-level season selector.

## Point aggregation
For every matchup, each side that has a finite score contributes the points of each player in
its **starters** list (bench players are ignored — only what was actually started counts). A
player's points are bucketed by their **real position** (`position`), not their lineup slot, so
**FLEX and superflex** points roll into the actual position (RB/WR/TE/QB) rather than a separate
FLEX bucket.

- Positions are **normalized** before bucketing: ESPN's `D/ST` becomes `DEF` via `POS_NORMALIZE`,
  matching the keys in `POSITION_COLORS`.
- The six standard positions get their own colored segment in fixed stacking order
  **QB → RB → WR → TE → DEF → K**. Any position without a dedicated color (e.g. IDP slots: LB,
  DB, …) folds into a single trailing **"Other"** segment (gray).
- A manager's **total** is the sum of all their starter points; bars are ordered by total
  descending, tie-broken on `ownerUsername.localeCompare` (the deterministic convention shared by
  the other analytics compute files).

## Score scope
**Every week counts** — regular-season *and* playoff weeks (bracket and consolation games alike).
Unlike the Power Rankings chart, playoff weeks are intentionally **included** so every manager
spans the same number of weeks and the totals reflect the whole season. The only matchups skipped
are **byes** (a side with no finite score) and **self-matchup placeholders**
(`team_a_id === team_b_id`), matching the existing compute guards.

## Scope
- Third chart on the existing `/analytics` page ([FE-033](FE-033-score-distribution-analytics.md)),
  driven by the same page-level season selector.
- Component: `PositionalScoring` wrapper + section in `src/features/analytics/analytics.tsx`;
  recharts stacked bar chart in `src/features/analytics/positional-scoring-chart.tsx`; pure
  transform in `src/features/analytics/compute-positional-scoring.ts`; data fetch reuses
  `getSeasonMatchups` (`MATCHUPS#{season}#`,
  [BE-005](../backend/BE-005-query-precomputed-views-api.md)).
- The chart is a **recharts `BarChart`** with `layout="vertical"` (horizontal bars, manager on the
  category axis) so long manager names stay legible (the category axis widens to fit the longest
  name), with one stacked `<Bar>` per present position. Segments are colored from the dedicated
  shared position palette (`positionColorMeta`, `src/lib/color-constants.ts`) so a position reads as
  its usual color across the app; the `.color` accents are tuned for mutual contrast (e.g. QB
  indigo vs DEF sky-blue) so adjacent stacked segments stay distinct, and the catch-all `'Other'`
  bucket gets its own accent. The tooltip and legend label positions by their abbreviation
  (QB/RB/WR/TE/**D/ST**/K/Other).
- The section has a plain **"Positional Scoring"** header (no info tooltip); hovering a bar reveals
  a per-position tooltip with that segment's points.
- **Premium-gated:** the section is wrapped in `SubscriptionGuard` with the shared
  `premium_feature` flag ([FE-021](FE-021-subscription-access-control.md) /
  [FE-026](FE-026-feature-flags.md)). With `billing` on but `premium_feature` off the guard is a
  pass-through and the chart renders for everyone; when gated and the subscription is
  expired/absent, the guard renders a blurred lock overlay in place of the chart and the gated
  component is **not mounted**, so its `MATCHUPS` data is never fetched while locked. Because the
  whole Analytics page is premium, while `billing` is off the **Analytics sidebar tab is hidden**.

## Edge Cases
- **Byes / odd team counts:** a matchup side with no finite score is skipped, and a self-matchup
  placeholder (`team_a_id === team_b_id`) is ignored, so neither inflates a manager's totals.
- **FLEX / superflex:** points are attributed to the player's real position, never a FLEX bucket.
- **IDP / unusual positions:** any position without a dedicated color folds into a single "Other"
  segment rather than being dropped.
- **Non-finite player points:** a starter whose `points_scored` is not a finite number counts as 0.
- **Season in progress:** bars reflect only the weeks played so far.
- **No `MATCHUPS` data (404) or load failure:** surface an inline message; never throw.
- **No matchup data at all:** show an empty-state message instead of an empty chart.
- **Locked (expired subscription):** the gated component is not mounted and never fetches.
- **Billing off:** the Analytics sidebar tab and page content are hidden entirely.

## Acceptance Criteria
- [ ] The Analytics page renders a **Positional Scoring** stacked bar chart below the power
      rankings, one bar per manager for the selected season, with a legend naming each position.
- [ ] Each bar's segments are the manager's summed starter points per **real position** (FLEX and
      superflex rolled into the actual position), with `D/ST` normalized to `DEF` and unrecognized
      positions grouped under "Other"; the aggregation is unit-tested.
- [ ] Bars are ordered by total points descending, tie-broken on `ownerUsername`.
- [ ] Every week (regular season and playoffs) contributes; byes and self-matchup placeholders are
      excluded.
- [ ] Switching the page season selector recomputes the chart.
- [ ] When `premium_feature` (and `billing`) is enabled and the league subscription is
      expired/absent, the section shows a blurred lock overlay instead of the chart and **does not
      fetch** the `MATCHUPS` data. With `billing` on but `premium_feature` off it renders for
      everyone; with `billing` off the Analytics tab is hidden.
- [ ] A `MATCHUPS` load failure renders an inline message, and a season with no matchup data
      renders an empty-state message — neither crashes.

## Sources
`src/features/analytics/` (`analytics.tsx`, `positional-scoring-chart.tsx`,
`compute-positional-scoring.ts`), `src/features/analytics/api-calls.ts` (`getSeasonMatchups`),
`src/lib/position-constants.ts` (`POS_NORMALIZE`), `src/lib/color-constants.ts`
(`positionColorMeta`), `src/features/subscription/subscription-guard.tsx`,
`src/features/subscription/subscription-required.tsx` (blurred lock overlay).
