# FE-033: Analytics Page (Premium)

## Description
A dedicated top-level **Analytics** page (`/analytics`, [FE-014](FE-014-navigation-sidebar.md)
sidebar tab) whose body is a stack of premium charts, all scoped to a single **page-level season
selector**. The whole page is premium: the sidebar tab and page body are gated together. Three
charts are stacked in order:

1. **Weekly Score Distribution** — a per-manager ridgeline ("joy") plot of weekly scores.
2. **Power Rankings** — a bump chart of each manager's weekly league rank.
3. **Positional Scoring** — a stacked horizontal bar chart of starter points split by position.

Everything is computed **entirely client-side** from the season's `MATCHUPS` view (the same data
the Matchups and Standings pages already fetch), so there is no backend, no new DynamoDB view, and
no API change. Each chart is a pure transform of an existing precomputed view, mirroring the
Schedule-Swap Simulator ([FE-031](FE-031-schedule-swap-simulator.md)) and Weekly Awards
([FE-032](FE-032-weekly-awards-superlatives.md)) pattern. Unlike FE-031/FE-032, which are premium
**sections embedded on existing pages**, the entire Analytics page is premium.

## Shared behavior (all charts)

### Premium gating
Each chart section is wrapped in its **own** `SubscriptionGuard` with the shared `premium_feature`
flag ([FE-021](FE-021-subscription-access-control.md) / [FE-026](FE-026-feature-flags.md)). With
`billing` on but `premium_feature` off the guard is a pass-through and the charts render for
everyone; when gated and the subscription is expired/absent, the guard renders a **blurred lock
overlay** in place of the chart and the gated component is **not mounted**, so its `MATCHUPS` data
is never fetched while locked. Because the **whole page** is premium, while `billing` is off the
**Analytics sidebar tab is hidden entirely** (the guard renders `null`, so the tab would otherwise
lead to a blank page) — the nav entry is gated on `isBillingEnabled`.

### Score scope (shared across all three charts)
Only **regular-season** weeks are included (`playoff_tier_type` is `NONE`/absent). Playoff weeks are
intentionally excluded so every manager's data uses a comparable sample — not everyone makes the
playoffs, and eliminated managers would otherwise have truncated/incomparable series. A side with no
finite score (a **bye**) and **self-matchup placeholders** (`team_a_id === team_b_id`) are skipped,
so byes never enter any computation. Managers are tie-broken on `ownerUsername.localeCompare` — the
deterministic convention shared across `compute-schedule-swap.ts` / `compute-awards.ts` and the
three analytics compute files.

### Shared edge cases
- **Byes / odd team counts:** a matchup side with no finite score is skipped, and a self-matchup
  placeholder is ignored, so neither enters any chart.
- **Season in progress:** every chart reflects only the regular-season weeks played so far.
- **No `MATCHUPS` data (404) or load failure:** surface an inline message; never throw.
- **No regular-season matchup data at all:** show an empty-state message instead of an empty chart.
- **Locked (expired subscription):** the gated component is not mounted and never fetches.
- **Billing off:** the Analytics sidebar tab and the whole page are hidden entirely.

## Chart 1 — Weekly Score Distribution (ridgeline / joy plot)
The page's first chart is a per-manager **ridgeline ("joy") plot** of weekly scores for the selected
season. Each manager gets their own overlapping density ridge — a smooth kernel-density curve of
their regular-season scores — stacked vertically and sorted by median, so the league can see the
*shape* of each distribution at a glance: who is steady (a tall, narrow ridge) vs. feast-or-famine
(a low, wide, or multi-modal ridge), and which "good" team is actually just high-variance. A
ridgeline reads the spread far more legibly than a row of side-by-side boxes, which is why it
replaced the earlier box-and-whisker rendering.

**Summary & density computation.** For each manager, collect their regular-season weekly scores
into one sorted array and compute:
- **Five-number summary + mean:** `min`, `q1`, `median`, `q3`, `max` using linear-interpolation
  quantiles (the d3/numpy "type 7" method) so quartiles fall between data points, plus the
  arithmetic `mean`. `iqr` is `q3 - q1`. These drive the hover tooltip.
- **Density curve:** a **Gaussian kernel-density estimate** sampled on a shared x-grid spanning the
  season's global score range (padded slightly). The bandwidth follows Silverman's rule of thumb —
  `0.9 * min(stdev, iqr/1.349) * n^(-1/5)` — falling back to a small fraction of the global range
  when the sample is degenerate (a single score or zero variance) so the ridge still renders as a
  visible bump instead of vanishing.

All managers share **one x-grid and one vertical density scale** (every ridge's height is scaled by
the single largest density across the league), so the heights are directly comparable, not per-row
normalized. Managers are sorted by **median descending**.

**Hover detail.** Because the chart is custom SVG (recharts has no native ridgeline plot), it
carries its own interactive tooltip. Hovering a manager's ridge (or focusing it via keyboard) shows
a cursor-anchored tooltip listing that manager's numbers — mean, median, min, max, and standard
deviation. The hovered ridge is subtly emphasized and a thin median marker is drawn on each ridge.
The tooltip is presentational; each ridge also exposes the same summary as an accessible label.

**Chart-1 edge cases:** *Single data point / zero variance* — the density falls back to a small
fraction of the global range so the ridge renders as a narrow bump rather than collapsing or
crashing.

## Chart 2 — Power Rankings (bump chart)
A **bump chart** of each manager's **weekly league rank** for the selected season, shown under the
header **"Power Rankings"**. Each manager is one line; the x-axis is the regular-season week and the
y-axis is the manager's rank that week (`1` = best, drawn at the top via a reversed axis), so the
league can watch the lines cross over as teams rise and fall.

The rank each week is derived by sorting managers on a transparent **power score** — a deliberately
**explainable blend, no black box** — of three components the league already understands: how often
you'd beat the rest of the league (all-play win%), how much you score (points-for), and how hot you
are right now (recency-weighted form).

**Power score computation.** The point plotted for a manager at week **W** uses every regular-season
week through **W** (cumulative), so each line is monotonic in information and the latest point is the
current power ranking. For each played week `w`, per manager:
- `pf_w` = that manager's score that week.
- `apf_w` = **all-play win fraction** that week = `(# managers with a strictly lower score that week
  + 0.5 × # ties) / (managersPlayedThatWeek − 1)`, in `[0, 1]` — the per-week "win% vs. league"
  already exposed at the season grain as `win_pct_vs_league` on the standings page.

Each component is normalized to a `0–100` scale and computed cumulatively through week W:
- **All-play win% (`AP`)** = `100 × mean(apf_w for w ≤ W)`.
- **Points-for strength (`PF`)** = `100 × (manager's cumulative average pf) / (league's highest
  cumulative average pf)` — your scoring as a share of the league's best scorer through that week
  (the leader is 100).
- **Recent form (`FORM`)** = `100 × Σ(weight_w × apf_w) / Σ(weight_w)` over recent weeks, with
  **exponential decay** (most recent week weight `1`, decaying by `0.6` per week back).

The blended score is `powerScore(W) = 0.50 × AP + 0.30 × PF + 0.20 × FORM`. Each week the blended
scores are sorted **descending** and turned into **1-based ranks** (`1` = best). The chart plots
those ranks, not the raw `0–100` score, so the axis reads as a familiar power ranking; the raw score
stays available for the tooltip. Lines/legend are ordered by **latest rank**. The **section header
carries an info tooltip** (the shared `Info` + `Tooltip` pattern) that spells out the blend
(50% all-play win%, 30% points-for, 20% recent form) in plain language, so the score is explainable
in-product.

**Rendering.** A recharts `LineChart` as a bump chart with a **reversed integer y-axis** (rank `1`
at top), mirroring the wins-progression chart on the standings page. Lines use `avatarColor` for
per-manager colors; an interactive legend lists each manager (real DOM, accessible) and clicking a
legend entry isolates that line.

**Chart-2 edge cases:** *Single week played* — every manager has one point; the chart renders a
single dot per line. *Fewer than two managers* — an empty-state message is shown (an all-play win%
needs at least one opponent).

## Chart 3 — Positional Scoring (stacked bar chart)
A **stacked horizontal bar chart**, one bar per manager, of each manager's **total starter points
for the selected season split by position**, shown under the header **"Positional Scoring"**. Bar
length is the manager's total starter points and each colored segment is one position's
contribution, so roster construction reads at a glance — who is carried by their RBs, whose QB slot
is a sinkhole, who is balanced.

**Point aggregation.** For every matchup, each side with a finite score contributes the points of
each player in its **starters** list (bench players are ignored — only what was actually started
counts). A player's points are bucketed by their **real position** (`position`), not their lineup
slot, so **FLEX and superflex** points roll into the actual position (RB/WR/TE/QB) rather than a
separate FLEX bucket.
- Positions are **normalized** before bucketing: ESPN's `D/ST` becomes `DEF` via `POS_NORMALIZE`,
  matching the keys in the shared position palette.
- The six standard positions get their own colored segment in fixed stacking order
  **QB → RB → WR → TE → DEF → K**. Any position without a dedicated color (e.g. IDP slots: LB, DB,
  …) folds into a single trailing **"Other"** segment (gray).
- A manager's **total** is the sum of all their starter points; bars are ordered by total
  descending.

**Rendering.** A recharts `BarChart` with `layout="vertical"` (horizontal bars, manager on the
category axis) so long manager names stay legible, with one stacked `<Bar>` per present position.
Segments are colored from the dedicated shared position palette (`positionColorMeta`,
`src/lib/color-constants.ts`), tuned for mutual contrast (e.g. QB indigo vs DEF sky-blue) so
adjacent stacked segments stay distinct; the catch-all `'Other'` bucket gets its own accent. The
tooltip and legend label positions by abbreviation (QB/RB/WR/TE/**D/ST**/K/Other). The header is
plain (no info tooltip); hovering a bar reveals a per-position tooltip with that segment's points.

**Chart-3 edge cases:** *FLEX / superflex* — points are attributed to the player's real position,
never a FLEX bucket. *IDP / unusual positions* — any position without a dedicated color folds into a
single "Other" segment rather than being dropped. *Non-finite player points* — a starter whose
`points_scored` is not a finite number counts as 0.

## Scope
- New page at `/analytics` ([FE-014](FE-014-navigation-sidebar.md) sidebar tab), scoped to a
  season selector (`src/features/season_select/season-select.tsx`).
- Page shell + section wrappers: `src/features/analytics/analytics.tsx`. All three sections read the
  season's `MATCHUPS` view via `getSeasonMatchups` (`MATCHUPS#{season}#`,
  [BE-005](../backend/BE-005-query-precomputed-views-api.md)) in `src/features/analytics/api-calls.ts`.
- Chart 1 — Score Distribution: custom SVG `joy-plot.tsx`; pure transform
  `compute-score-distribution.ts`. (Custom SVG because recharts has no native ridgeline chart;
  uses `TeamAvatar` + `avatarColor` for per-manager ridge labels.)
- Chart 2 — Power Rankings: recharts line chart `power-rankings-chart.tsx`; pure transform
  `compute-power-rankings.ts`.
- Chart 3 — Positional Scoring: recharts stacked bar chart `positional-scoring-chart.tsx`; pure
  transform `compute-positional-scoring.ts`; `src/lib/position-constants.ts` (`POS_NORMALIZE`),
  `src/lib/color-constants.ts` (`positionColorMeta`).
- **Premium-gated (whole page):** see *Shared behavior → Premium gating* above. Nav entry gated on
  `isBillingEnabled` ([FE-026](FE-026-feature-flags.md)); each section wrapped in
  `SubscriptionGuard` with the shared `premium_feature` flag.

## Acceptance Criteria
- [ ] An **Analytics** tab appears in the sidebar (when `billing` is on) and routes to `/analytics`;
      switching the page season selector recomputes all three charts.
- [ ] **Score Distribution:** renders a per-manager ridgeline (joy) chart, one overlapping Gaussian
      KDE ridge per manager on a shared x-grid and shared vertical scale, sorted by median
      descending; hovering/keyboard-focusing a ridge reveals that manager's numeric summary with an
      equivalent accessible label; the quartile and density math is unit-tested.
- [ ] **Power Rankings:** renders a bump chart, one line per manager plotting weekly league rank
      (`1` = best, top of a reversed y-axis) from the cumulative power score
      `0.50×AP + 0.30×PF + 0.20×FORM`, lines/legend ordered by latest rank; the math and ranking are
      unit-tested; a header info tooltip explains the blend.
- [ ] **Positional Scoring:** renders a stacked horizontal bar per manager of summed starter points
      per **real position** (FLEX/superflex rolled into the actual position; `D/ST` normalized to
      `DEF`; unrecognized positions grouped under "Other"), bars ordered by total descending; the
      aggregation is unit-tested.
- [ ] Across all three charts, only regular-season weeks contribute; byes and self-matchup
      placeholders are excluded.
- [ ] When `premium_feature` (and `billing`) is enabled and the league subscription is
      expired/absent, each section shows a blurred lock overlay instead of the chart and **does not
      fetch** the `MATCHUPS` data. With `billing` on but `premium_feature` off the charts render for
      everyone; with `billing` off the Analytics tab is hidden.
- [ ] A `MATCHUPS` load failure renders an inline message, and a season with no regular-season
      matchup data (or, for Power Rankings, fewer than two managers) renders an empty-state message —
      neither crashes.

## Sources
`src/features/analytics/` (`analytics.tsx`, `api-calls.ts`, `joy-plot.tsx`,
`compute-score-distribution.ts`, `power-rankings-chart.tsx`, `compute-power-rankings.ts`,
`positional-scoring-chart.tsx`, `compute-positional-scoring.ts`), `src/app/app.tsx` (route),
`src/features/sidebar/app-sidebar.tsx` (nav item), `src/features/season_select/season-select.tsx`,
`src/lib/position-constants.ts` (`POS_NORMALIZE`), `src/lib/color-constants.ts`
(`avatarColor`, `positionColorMeta`), `src/features/subscription/subscription-guard.tsx`,
`src/features/subscription/subscription-required.tsx` (blurred lock overlay).
