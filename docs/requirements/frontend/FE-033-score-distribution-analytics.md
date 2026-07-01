# FE-033: Weekly Score Distribution (Analytics)

## Description
A new top-level **Analytics** page (`/analytics`) whose first chart is a per-manager
**ridgeline ("joy") plot** of weekly scores for the selected season. Each manager gets their
own overlapping density ridge — a smooth kernel-density curve of their regular-season scores —
stacked vertically and sorted by median, so the league can see at a glance the *shape* of each
distribution: who is steady (a tall, narrow ridge) vs. who is feast-or-famine (a low, wide or
multi-modal ridge), and which "good" team is actually just high-variance. A ridgeline reads the
spread far more legibly than a row of side-by-side boxes, which is why it replaces the earlier
box-and-whisker rendering.

Everything is computed **entirely client-side** from the season's `MATCHUPS` view (the same
data the Matchups and Standings pages already fetch), so there is no backend, no new DynamoDB
view, and no API change. It mirrors the Schedule-Swap Simulator
([FE-031](FE-031-schedule-swap-simulator.md)) and Weekly Awards
([FE-032](FE-032-weekly-awards-superlatives.md)) pattern: a pure transform of an existing
precomputed view, gated behind `SubscriptionGuard`.

Unlike FE-031/FE-032, which are premium **sections embedded on existing pages**, the entire
Analytics page is premium: it is a dedicated sidebar tab whose body is the gated content.

## Summary & density computation
For each manager, collect their regular-season weekly scores into one sorted array and compute:
- **Five-number summary + mean:** `min`, `q1`, `median`, `q3`, `max` using
  linear-interpolation quantiles (the d3/numpy "type 7" method) so quartiles fall between data
  points, plus the arithmetic `mean`. `iqr` is `q3 - q1`. These drive the hover tooltip.
- **Density curve:** a **Gaussian kernel-density estimate** sampled on a shared x-grid spanning
  the season's global score range (padded slightly). The bandwidth follows Silverman's
  rule of thumb — `0.9 * min(stdev, iqr/1.349) * n^(-1/5)` — falling back to a small fraction of
  the global range when the sample is degenerate (a single score or zero variance) so the ridge
  still renders as a visible bump instead of vanishing.

All managers share **one x-grid and one vertical density scale** (every ridge's height is scaled
by the single largest density across the league), so a steadier manager literally draws a taller,
narrower ridge and a volatile one draws a lower, flatter ridge — the heights are directly
comparable, not per-row normalized.

Managers are sorted by **median descending**, tie-broken on `ownerUsername.localeCompare`
(matching the deterministic tiebreak convention in `compute-schedule-swap.ts` /
`compute-awards.ts`).

## Hover detail
Because the chart is custom SVG (recharts has no native ridgeline plot), it carries its own
interactive tooltip rather than relying on the browser's native `<title>` hint. Hovering a
manager's ridge (or focusing it via keyboard) shows a cursor-anchored tooltip listing that
manager's numbers — mean, median, min, max, and standard deviation — so the values behind each
ridge are readable, not just visually comparable. The hovered ridge is
subtly emphasized and a thin median marker is drawn on each ridge. The tooltip is presentational;
each ridge also exposes the same summary as an accessible label.

## Score scope
Only **regular-season** weeks are included (`playoff_tier_type` is `NONE`/absent). Playoff
weeks are intentionally excluded so every manager's distribution uses a comparable sample — not
everyone makes the playoffs, and eliminated managers would otherwise have far fewer data points,
making the ridges incomparable. A side with no finite score (a bye) and self-matchup
placeholders (`team_a_id === team_b_id`) are skipped, so byes never enter a distribution.

## Scope
- New page at `/analytics` ([FE-014](FE-014-navigation-sidebar.md) sidebar tab), scoped to a
  season selector.
- Component: `src/features/analytics/analytics.tsx`; custom SVG chart in `joy-plot.tsx`; pure
  transform in `compute-score-distribution.ts`; data fetch reuses `getSeasonMatchups`
  (`MATCHUPS#{season}#`, [BE-005](../backend/BE-005-query-precomputed-views-api.md)).
- The ridgeline plot is a **custom SVG component** (recharts has no native ridgeline chart),
  using `TeamAvatar` + `avatarColor` for per-manager ridge labels, consistent with the other
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
  self-matchup placeholder (`team_a_id === team_b_id`) is ignored, so byes never enter a ridge.
- **Single data point / zero variance:** a manager with one regular-season score (or many
  identical scores) has no spread to estimate a bandwidth from; the density falls back to a
  small fraction of the global range so the ridge renders as a narrow bump rather than
  collapsing to nothing or crashing.
- **Season in progress:** the distribution reflects only the regular-season weeks played so far.
- **No `MATCHUPS` data (404) or load failure:** surface an inline message; never throw.
- **No regular-season matchup data at all:** show an empty-state message instead of an empty
  chart.
- **Locked (expired subscription):** the gated component is not mounted and never fetches.
- **Billing off:** the Analytics sidebar tab and page content are hidden entirely.

## Acceptance Criteria
- [ ] An **Analytics** tab appears in the sidebar (when `billing` is on) and routes to
      `/analytics`.
- [ ] The page renders a per-manager ridgeline (joy) chart for the selected season, one
      overlapping density ridge per manager, sorted by median descending, showing each
      manager's name/label.
- [ ] Each ridge is a Gaussian KDE of that manager's regular-season scores on a shared x-grid
      and shared vertical scale; the underlying quartile and density math is unit-tested.
- [ ] Hovering (or keyboard-focusing) a manager's ridge reveals a tooltip with that manager's
      numeric summary; the ridge carries an equivalent accessible label.
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
