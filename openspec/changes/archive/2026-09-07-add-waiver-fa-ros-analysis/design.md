## Context

See proposal.md — Why. The trade ROS analysis already exists in
`frontend/src/features/transactions/transactions.tsx` (`TransactionCard`, `TeamPanel`) and computes
points client-side via `buildWeeklyPlayerPoints` + `rosPointsFor` over the season's `MATCHUPS` box
scores (`frontend/src/features/transactions/api-calls.ts`). Today `TransactionCard` only passes the
`weekly` map to a panel for two-team trades, and `TeamPanel` renders points on add rows but not drop
rows. Waivers/free agents are single-roster moves that already render both add and drop rows.

## Goals / Non-Goals

**Goals:**
- Reuse the existing `rosPointsFor` semantics unchanged for waiver/free-agent adds and drops.
- Keep trade behavior (two-team side totals + winner banner) exactly as-is.

**Non-Goals:**
- No new ROS helper, backend, API, or DynamoDB work.
- No ROS for multi-team (>2 roster) trades or commissioner moves (the wire never lists the latter).

## Decisions

- **Drop points use the same window as adds** (`rosPointsFor(player_id, txn.week, weekly)`): a
  dropped player's "rest-of-season" is what they scored from the transaction week onward, following
  the player across later roster moves — identical semantics to trade adds. Alternative (freeze at
  the drop week) rejected: it would answer a different, less useful question ("what you gave up").
- **Net pickup value = added total − dropped total**, shown only when the move has both an add and a
  drop, rendered in the single roster panel's footer (reusing the existing `mt-2.5 pt-2 border-t`
  footer markup used for the trade side total). Positive → emerald, negative → red, zero → "Even".
  A pure add or pure drop shows only the per-player points (the number is self-explanatory; a net
  of a single side would be redundant).
- **Gating stays in `TransactionCard`**: pass `weekly` to the panel when box scores are available
  for two-team trades (unchanged) or any non-trade move (new). The trade `sideTotal`/`isWinner`
  props remain set only on the two-team-trade path, so the trade side-total footer (gated on
  `sideTotal != null`) and the new waiver/FA net footer (gated on `!isTrade && adds && drops`) never
  collide.

## Risks / Trade-offs

- A dropped player who is never re-rostered contributes 0 — matches `rosPointsFor`'s existing
  behavior for unrostered players and is the correct outcome. → No mitigation needed.
- Box scores may be missing for a season (same as trades today) → the panel already degrades
  silently; the net footer and per-row points are gated on `weekly != null`, so nothing renders and
  no error is shown.
