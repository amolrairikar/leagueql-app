# FE-033: Weekly Score Distribution (Analytics)

## Description
A new top-level **Analytics** page (`/analytics`) whose first chart is a per-manager
**box-and-whisker** plot of weekly scores for the selected season. Each manager's box shows
the median, interquartile range (IQR), whiskers, and outliers side by side, sorted by median,
so the league can see at a glance who is steady vs. who is feast-or-famine — and which "good"
team is actually just high-variance.

Everything is computed **entirely client-side** from the season's `MATCHUPS` view (the same
data the Matchups and Standings pages already fetch), so there is no backend, no new DynamoDB
view, and no API change. It mirrors the Schedule-Swap Simulator
([FE-031](FE-031-schedule-swap-simulator.md)) and Weekly Awards
([FE-032](FE-032-weekly-awards-superlatives.md)) pattern: a pure transform of an existing
precomputed view, gated behind `SubscriptionGuard`.

Unlike FE-031/FE-032, which are premium **sections embedded on existing pages**, the entire
Analytics page is premium: it is a dedicated sidebar tab whose body is the gated content.

## Quartile & whisker computation
For each manager, collect their regular-season weekly scores into one sorted array and compute:
- **Five-number summary:** `min`, `q1`, `median`, `q3`, `max` using linear-interpolation
  quantiles (the d3/numpy "type 7" method) so quartiles fall between data points.
- **IQR:** `q3 - q1`, with **Tukey fences** at `q1 - 1.5*iqr` and `q3 + 1.5*iqr`.
- **Whisker ends:** the most extreme scores that still fall **within** the fences (the box's
  "min/max" lines are these whisker ends, not the raw min/max).
- **Outliers:** any score outside the fences, drawn as individual dots beyond the whiskers.

Managers are sorted by **median descending**, tie-broken on `ownerUsername.localeCompare`
(matching the deterministic tiebreak convention in `compute-schedule-swap.ts` /
`compute-awards.ts`).

## Score scope
Only **regular-season** weeks are included (`playoff_tier_type` is `NONE`/absent). Playoff
weeks are intentionally excluded so every manager's distribution uses a comparable sample — not
everyone makes the playoffs, and eliminated managers would otherwise have far fewer data points,
making the boxes incomparable. A side with no finite score (a bye) and self-matchup
placeholders (`team_a_id === team_b_id`) are skipped, so byes never enter a distribution.

## Scope
- New page at `/analytics` ([FE-014](FE-014-navigation-sidebar.md) sidebar tab), scoped to a
  season selector.
- Component: `src/features/analytics/analytics.tsx`; custom SVG chart in `box-plot.tsx`; pure
  transform in `compute-score-distribution.ts`; data fetch reuses `getSeasonMatchups`
  (`MATCHUPS#{season}#`, [BE-005](../backend/BE-005-query-precomputed-views-api.md)).
- The box plot is a **custom SVG component** (recharts has no native box-and-whisker chart),
  using `TeamAvatar` + `avatarColor` for per-manager row labels, consistent with the other
  charts.
- **Premium-gated (whole page):** the page body is wrapped in `SubscriptionGuard` with the
  shared `premium_feature` flag ([FE-021](FE-021-subscription-access-control.md) /
  [FE-026](FE-026-feature-flags.md)). With `billing` on but `premium_feature` off the guard is
  a pass-through and the page renders for everyone; when gated and the subscription is
  expired/absent, the guard renders a blurred lock overlay in place of the chart and the gated
  component is **not mounted**, so its `MATCHUPS` data is never fetched while locked. Because
  the entire page is the gated feature, while `billing` is off the **Analytics sidebar tab is
  hidden** (the guard renders `null`, so the tab would otherwise lead to a blank page) — the
  nav entry is gated on `isBillingEnabled`.

## Edge Cases
- **Byes / odd team counts:** a matchup where a side has no valid score is skipped, and a
  self-matchup placeholder (`team_a_id === team_b_id`) is ignored, so byes never enter a box.
- **Single data point:** a manager with one regular-season score has a degenerate box (all
  five numbers equal); it still renders as a single tick rather than crashing.
- **Season in progress:** the distribution reflects only the regular-season weeks played so far.
- **No `MATCHUPS` data (404) or load failure:** surface an inline message; never throw.
- **No regular-season matchup data at all:** show an empty-state message instead of an empty
  chart.
- **Locked (expired subscription):** the gated component is not mounted and never fetches.
- **Billing off:** the Analytics sidebar tab and page content are hidden entirely.

## Acceptance Criteria
- [ ] An **Analytics** tab appears in the sidebar (when `billing` is on) and routes to
      `/analytics`.
- [ ] The page renders a per-manager box-and-whisker chart for the selected season, one row
      per manager, sorted by median descending, showing each manager's name/label.
- [ ] Each box reflects the five-number summary with Tukey-fence whiskers and outlier dots as
      described; the underlying quartile math is unit-tested.
- [ ] Switching the season selector recomputes the chart.
- [ ] Byes and self-matchup placeholders are excluded; playoff weeks are excluded.
- [ ] When `premium_feature` (and `billing`) is enabled and the league subscription is
      expired/absent, the page shows a blurred lock overlay instead of the chart and **does not
      fetch** the `MATCHUPS` data. With `billing` on but `premium_feature` off it renders for
      everyone; with `billing` off the Analytics tab is hidden.
- [ ] A `MATCHUPS` load failure renders an inline message, and a season with no regular-season
      matchup data renders an empty-state message — neither crashes.

## Sources
`src/features/analytics/`, `src/app/app.tsx` (route), `src/features/sidebar/app-sidebar.tsx`
(nav item), `src/features/season_select/season-select.tsx`,
`src/features/subscription/subscription-guard.tsx`,
`src/features/subscription/subscription-required.tsx` (blurred lock overlay).
