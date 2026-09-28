# Design

## Context

`/transactions` loads the season's transactions, standings, and `MATCHUPS` box scores in parallel.
`buildWeeklyPlayerPoints` + `rosPointsFor` (`api-calls.ts`) already give each player's
rest-of-season (ROS) points, and the transaction cards compute a two-team trade's per-side totals
(`sideTotal`) and a waiver/free-agent move's net pickup value inline in `TeamPanel`. The UI
direction (a row of five stat tiles) was settled in a mockup review.

## Goals / Non-Goals

**Goals:**
- One combined top-5 across waivers, free agents, and trades, ranked on a single points scale.
- The tile numbers always match the numbers shown on the corresponding transaction card.

**Non-Goals:**
- Any backend precomputation or new view.
- Ranking multi-team (>2 roster) trades or commissioner moves (the cards show no ROS for them).
- Making the highlight follow the type filter.

## Decisions

- **Impact metric.** Waiver/free agent: the net pickup value (adds' ROS − drops' ROS) for the single
  roster. Two-team trade: `|sideA − sideB|`, credited to the higher-scoring roster. Both are in
  fantasy points, so they rank on one scale. Alternative considered: acquired ROS only (ignoring
  drops / what a trade gave up) — rejected because it rewards churn rather than good decisions and
  would disagree with the numbers on the cards.
- **Eligibility.** Impact must be > 0: even trades, net-zero or net-negative pickups are not
  "top" moves. Ties sort by earlier `created` (the earlier move got there first).
- **Shared helpers.** The ROS math moves into `transaction-impact.ts` (`sideTotal`,
  `netPickupValue`, `transactionImpact`, `topTransactions`), and both the cards and the tiles call it,
  so they can never drift apart. `TYPE_META` moves to `type-meta.ts` so the tile component can reuse
  the chips without importing the page module.
- **Layout.** `grid-cols-2 sm:grid-cols-3 lg:grid-cols-5`; the #1 tile spans two columns on the
  2-column (mobile) layout and carries an emerald tint.

## Risks / Trade-offs

- Early-season moves accumulate more ROS weeks than late ones, so the list skews early. Accepted —
  it is literally "which moves produced the most points", matching the cards.
- Players absent from every box score in a week count as 0 for that week (existing ROS limitation).
