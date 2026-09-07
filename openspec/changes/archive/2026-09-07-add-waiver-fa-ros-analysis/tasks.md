## 1. Component changes (transactions.tsx)

- [x] 1.1 In `TransactionCard`, pass the `weekly` map to the panel for non-trade moves too (when box
  scores are available), keeping trade `sideTotal`/`isWinner`/winner-banner gating unchanged; verify
  multi-team trades still receive no ROS.
- [x] 1.2 In `TeamPanel`, render ROS points on drop rows (mirroring add rows) via
  `rosPointsFor(p.player_id, tradeWeek, weekly)` when `showRos`.
- [x] 1.3 In `TeamPanel`, add a net pickup footer for non-trade moves with both an add and a drop:
  `net = round2(addTotal - dropTotal)`, labeled "Net pickup value", signed and colored
  (emerald/red/"Even"); verify it does not render for pure adds or pure drops.

## 2. Component tests (__tests__/transactions.feature + transactions.steps.test.tsx)

- [x] 2.1 Add fixtures: a free-agent move with an add + drop, a pure-add move, and a pure-drop move,
  plus matching `MATCHUPS` box scores (reuse `mkMatchup`).
- [x] 2.2 Add scenarios for: add+drop shows both players' ROS points and the net pickup value; pure
  add shows only the added player's points with no net; pure drop shows only the dropped player's
  points with no net; waiver/FA renders without points/net when box scores are unavailable (no
  error). Steps must select the Free Agents (or Waivers) filter.
- [x] 2.3 Run `npx vitest run src/features/transactions/__tests__/transactions.steps.test.tsx` from
  `frontend/` and verify all scenarios (existing trade + new waiver/FA) pass.

## 3. Quality gates

- [x] 3.1 From `frontend/`, run `npm run format:fix` and `npm run lint` with no errors.
- [x] 3.2 From repo root, run `openspec validate add-waiver-fa-ros-analysis --strict` and verify it
  passes.
