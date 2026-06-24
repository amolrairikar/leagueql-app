# FE-034: Power Rankings Trend (Analytics)

## Description
A second chart on the premium **Analytics** page (`/analytics`), shown under the header
**"Power Rankings"**: a **bump chart** of each manager's **weekly league rank** for the selected
season. Each manager is one line; the x-axis is the regular-season week and the y-axis is the
manager's rank that week (`1` = best, drawn at the top via a reversed axis), so the league can
watch the lines cross over as teams rise and fall.

The rank each week is derived by sorting managers on a transparent **power score** — a
deliberately **explainable blend — no black box** — of three components
the league already understands: how often you'd beat the rest of the league (all-play win%),
how much you score (points-for), and how hot you are right now (recency-weighted form). The
exact weights and inputs are documented below and surfaced in the UI.

Everything is computed **entirely client-side** from the season's `MATCHUPS` view (the same
data the Score Distribution chart, Matchups, and Standings pages already fetch), so there is no
backend, no new DynamoDB view, and no API change. It mirrors the Score Distribution
([FE-033](FE-033-score-distribution-analytics.md)), Schedule-Swap Simulator
([FE-031](FE-031-schedule-swap-simulator.md)), and Weekly Awards
([FE-032](FE-032-weekly-awards-superlatives.md)) pattern: a pure transform of an existing
precomputed view, gated behind `SubscriptionGuard`. It renders as a **second stacked section**
below the box-and-whisker chart on the same Analytics page, under its own
`SubscriptionGuard`, driven by the same page-level season selector.

## Power score computation
The point plotted for a manager at week **W** uses every regular-season week through **W**
(cumulative), so each line is monotonic in information and the latest point is the current
power ranking. For each played week `w`, per manager:
- `pf_w` = that manager's score that week.
- `apf_w` = **all-play win fraction** that week = `(# managers with a strictly lower score that
  week + 0.5 × # ties) / (managersPlayedThatWeek − 1)`, in `[0, 1]`. This is the per-week
  "win% vs. league" already exposed at the season grain as `win_pct_vs_league` on the standings
  page.

Each component is normalized to a `0–100` scale and computed cumulatively through week W:
- **All-play win% (`AP`)** = `100 × mean(apf_w for w ≤ W)`.
- **Points-for strength (`PF`)** = `100 × (manager's cumulative average pf) / (league's highest
  cumulative average pf)` — your scoring as a share of the league's best scorer through that
  week (the leader is 100). Bounded, explainable, and chart-friendly.
- **Recent form (`FORM`)** = `100 × Σ(weight_w × apf_w) / Σ(weight_w)` over recent weeks, with
  **exponential decay** (most recent week weight `1`, decaying by `0.6` per week back). Captures
  who is hot or cold right now without a hard window cutoff.

The blended score is:

```
powerScore(W) = 0.50 × AP + 0.30 × PF + 0.20 × FORM
```

Each week the blended scores are sorted **descending** (tie-broken on
`ownerUsername.localeCompare`, matching the deterministic convention in
`compute-schedule-swap.ts` / `compute-awards.ts` / `compute-score-distribution.ts`) and turned
into **1-based ranks** (`1` = best). The chart plots those ranks, not the raw `0–100` score, so
the axis reads as a familiar power ranking; the raw score stays available for the tooltip.
Managers (the line ordering / legend) are sorted by their **latest rank**.

## Score scope
Only **regular-season** weeks are included (`playoff_tier_type` is `NONE`/absent). Playoff weeks
are intentionally excluded so every manager's line spans the same weeks and stays comparable —
not everyone makes the playoffs, and eliminated managers would otherwise have truncated lines. A
side with no finite score (a bye) and self-matchup placeholders (`team_a_id === team_b_id`) are
skipped, so byes never enter a week's all-play pool or scoring average.

## Scope
- Second chart on the existing `/analytics` page ([FE-033](FE-033-score-distribution-analytics.md)),
  driven by the same page-level season selector.
- Component: `PowerRankings` wrapper + section in `src/features/analytics/analytics.tsx`;
  recharts line chart in `src/features/analytics/power-rankings-chart.tsx`; pure transform in
  `src/features/analytics/compute-power-rankings.ts`; data fetch reuses `getSeasonMatchups`
  (`MATCHUPS#{season}#`, [BE-005](../backend/BE-005-query-precomputed-views-api.md)).
- The chart is a **recharts `LineChart`** as a bump chart with a **reversed integer y-axis**
  (rank `1` at the top), mirroring the wins-progression chart on the standings page (recharts is
  already a dependency). Lines use `avatarColor` for per-manager colors, consistent with the
  other charts; an interactive legend lists each manager so labels are real DOM (accessible, not
  dependent on chart measurement) and clicking a legend entry isolates that line.
- The **section header carries an info tooltip** (the shared `Info` + `Tooltip` pattern) that
  spells out the transparent blend (50% all-play win%, 30% points-for, 20% recent form) in plain
  language, so the score is explainable in-product rather than a black box.
- **Premium-gated:** the section is wrapped in `SubscriptionGuard` with the shared
  `premium_feature` flag ([FE-021](FE-021-subscription-access-control.md) /
  [FE-026](FE-026-feature-flags.md)). With `billing` on but `premium_feature` off the guard is a
  pass-through and the chart renders for everyone; when gated and the subscription is
  expired/absent, the guard renders a blurred lock overlay in place of the chart and the gated
  component is **not mounted**, so its `MATCHUPS` data is never fetched while locked. Because the
  whole Analytics page is premium, while `billing` is off the **Analytics sidebar tab is hidden**
  (the nav entry is gated on `isBillingEnabled`).

## Edge Cases
- **Byes / odd team counts:** a matchup where a side has no valid score is skipped, and a
  self-matchup placeholder (`team_a_id === team_b_id`) is ignored, so byes never enter a week's
  all-play pool.
- **Single week played:** every manager has one point; the chart renders a single dot per line
  rather than crashing.
- **Fewer than two managers:** an empty-state message is shown instead of a degenerate chart
  (an all-play win% needs at least one opponent).
- **Season in progress:** lines reflect only the regular-season weeks played so far.
- **No `MATCHUPS` data (404) or load failure:** surface an inline message; never throw.
- **No regular-season matchup data at all:** show an empty-state message instead of an empty
  chart.
- **Locked (expired subscription):** the gated component is not mounted and never fetches.
- **Billing off:** the Analytics sidebar tab and page content are hidden entirely.

## Acceptance Criteria
- [ ] The Analytics page renders a **Power Rankings** bump chart below the score distribution,
      one line per manager for the selected season, with a legend naming each manager.
- [ ] Each manager's line plots their **weekly league rank** (`1` = best, top of a reversed
      y-axis), where the rank comes from sorting on the cumulative power score
      `0.50×AP + 0.30×PF + 0.20×FORM`; the underlying math and ranking are unit-tested.
- [ ] Lines/legend are ordered by latest rank, tie-broken on `ownerUsername`.
- [ ] Switching the page season selector recomputes the chart.
- [ ] Byes and self-matchup placeholders are excluded; playoff weeks are excluded.
- [ ] When `premium_feature` (and `billing`) is enabled and the league subscription is
      expired/absent, the section shows a blurred lock overlay instead of the chart and **does
      not fetch** the `MATCHUPS` data. With `billing` on but `premium_feature` off it renders for
      everyone; with `billing` off the Analytics tab is hidden.
- [ ] A `MATCHUPS` load failure renders an inline message, and a season with fewer than two
      managers' worth of regular-season data renders an empty-state message — neither crashes.

## Sources
`src/features/analytics/` (`analytics.tsx`, `power-rankings-chart.tsx`,
`compute-power-rankings.ts`), `src/features/analytics/api-calls.ts` (`getSeasonMatchups`),
`src/lib/color-constants.ts` (`avatarColor`),
`src/features/subscription/subscription-guard.tsx`,
`src/features/subscription/subscription-required.tsx` (blurred lock overlay).
