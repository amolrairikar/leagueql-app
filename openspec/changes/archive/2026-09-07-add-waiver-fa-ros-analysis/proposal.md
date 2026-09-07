## Why

The `/transactions` page already analyzes trades by showing each acquired player's rest-of-season
(ROS) fantasy points and a per-side winner, but waivers and free-agent moves show only the added
(green) and dropped (red) player names with no scoring insight. Managers can't see whether a
pickup or drop actually paid off. The ROS building blocks (`buildWeeklyPlayerPoints`,
`rosPointsFor`) already exist and are reused for trades, so extending the same analysis to
waivers/free agents is low-cost.

## What Changes

- On the `/transactions` waiver and free-agent cards, show the ROS fantasy points next to each
  **added** and **dropped** player (points scored from the transaction's week through the end of
  the season, following the player regardless of later roster moves).
- When a move has **both** an add and a drop, show a **net pickup value** (added ROS − dropped ROS)
  in the panel footer.
- A **pure add** or **pure drop** shows only that one player's ROS points, with no net footer.
- When the season's matchup box scores are unavailable, waiver/free-agent cards render in their
  normal form with no points, no net, and no error — matching the existing trade fallback.
- All computed client-side from the season's `MATCHUPS` box scores; no backend/API/DynamoDB change.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `frontend/transactions`: add a requirement for waiver and free-agent rest-of-season points
  (per-player ROS on adds/drops, plus a net pickup value when both are present).

## Impact

- Frontend only: `frontend/src/features/transactions/transactions.tsx` (`TransactionCard`,
  `TeamPanel`); reuses `rosPointsFor` / `buildWeeklyPlayerPoints` from
  `frontend/src/features/transactions/api-calls.ts` (no change there).
- Component tests: `frontend/src/features/transactions/__tests__/transactions.feature` +
  `transactions.steps.test.tsx` gain waiver/free-agent ROS scenarios and fixtures.
- No backend, API contract, DynamoDB schema, or architecture changes.
