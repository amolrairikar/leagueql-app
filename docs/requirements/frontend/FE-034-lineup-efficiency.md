# FE-034: Lineup Efficiency / Points Left on the Bench

## Description
A free **chip in the box score**, shown directly below each team's logo/name, that answers
the league's eternal "my lineups betray me" argument: **how many points did this manager leave
on the bench by starting the wrong players?**

For the team-week shown in that box score it computes, entirely client-side, the **optimal
legal starting lineup** from the combined `starters + bench` pool and compares it to what the
manager actually started:
- The chip reads **`⚡ {N}% efficient`** (lineup-efficiency % = actual points ÷ optimal points).
- Clicking it opens a **Start/Sit Report** dialog listing the slot-by-slot mistakes — for each
  suboptimal slot, who was started, who was the optimal choice, and the point delta — plus a
  footer with total **points left on the bench** and the efficiency %.

The single hard nuance versus a naive "top-N scores" calculation is positional **slot
eligibility** (FLEX/superflex), so the optimizer respects the league's roster slots (see
[Lineup optimizer algorithm](#lineup-optimizer-algorithm)).

## Scope
- Lives in the shared box-score component (`src/components/box-score-card.tsx`), so it appears
  everywhere a box score renders (matchups [FE-006], playoff bracket, manager history, player
  records, manager comparison, matchup records). The chip is self-contained: it sources league
  context from cookies and adds **no new props** to those call sites.
- Pure transform of the box score's own `starters` / `bench` (with per-player `points_scored`,
  `position`, and the starter's `fantasy_position` slot) — **no new data fetch** of any kind.
  Component: `src/features/lineup_efficiency/lineup-efficiency-chip.tsx`; pure transform in
  `compute-lineup-efficiency.ts`.
- **Free:** the chip always renders (regardless of `billing`, subscription, or demo mode); the
  only reason it shows nothing is a lack of bench data to measure. It carries no subscription
  gating and does not read the subscription primitives.

## Lineup optimizer algorithm
- **Slot template:** there is no stored per-league roster configuration anywhere queryable, so
  the league's starting-slot template for the team-week is derived by tallying the
  `fantasy_position` of each actual starter (one slot instance per starter, e.g.
  `[QB, RB, RB, WR, WR, TE, FLEX, K, D/ST]`). Bench players carry no `fantasy_position`.
- **Eligibility:** a `SLOT_ELIGIBILITY` map encodes which real positions may fill each slot
  (FLEX = {RB,WR,TE}; OP/superflex = {QB,RB,WR,TE}; "WR/TE" = {WR,TE}; "RB/WR" = {RB,WR};
  dedicated slots = that position only; plus IDP slots). Positions and slot labels are normalized
  with the shared `POS_NORMALIZE` (`D/ST` → `DEF`) so ESPN/Sleeper defense labels unify. An
  unknown slot label falls back to matching only its own position, so it can never crash the
  optimizer.
- **Optimum (exact, not greedy):** the eligibility sets are **non-laminar** (an "RB/WR" slot's
  {RB,WR} overlaps a "WR/TE" slot's {WR,TE} without nesting), so a greedy "fill the
  most-restrictive slot with its best eligible player" can be strictly suboptimal. The optimal
  lineup is therefore found as an exact **maximum-weight bipartite matching** of slots ↔ players
  via min-cost max-flow (player→slot edge weight = the player's points; scaled to integers for
  float-stable relaxation). Only **improving** augmentations are taken, so a slot whose only
  eligible players score negative is left empty (0) rather than filled at a loss — matching real
  "best legal lineup" semantics.
- **Efficiency %** = actual starter points ÷ optimal points, clamped to [0, 1]; reported as 100%
  when optimal points are 0 (no measurable loss). **Points left on the bench** = optimal −
  actual (never negative). The per-slot report deltas always sum to points-left.

## Start/Sit report
- Built by aligning, within each slot label, the actual starters and the optimal players (both
  sorted best-first), so each row is one slot instance; rows with `delta > 0` are the start/sit
  mistakes shown in the dialog. Ties broken by `player_id` for deterministic output.
- When no row changed, the dialog shows a "Perfect lineup — nothing left on the bench" state.

## Edge Cases
- **No bench data** (ESPN seasons before 2018, or a genuinely empty bench): efficiency cannot be
  measured, so the chip renders **nothing** (mirrors the existing "Bench data unavailable" note
  in the box score).
- **Perfect lineup:** optimal == actual → chip shows 100%; dialog shows the perfect-lineup state.
- **Players ineligible for any open slot / short or injured rosters:** ineligible players are
  simply never matched; unfillable slots contribute 0; optimal is always ≥ actual.
- **Negative-scoring players:** the optimizer may leave a slot empty rather than start a
  net-negative player.
- **Mixed-platform defense labels** (`D/ST` vs `DEF`): normalized so either fills the defense slot.

## Acceptance Criteria
- [ ] In a box score with bench data, each team shows a lineup-efficiency chip below its name.
- [ ] The chip reads `{N}% efficient`; clicking opens a Start/Sit Report listing the
      suboptimal slots (started vs optimal player and the point delta) and the points-left footer.
- [ ] The optimal lineup respects FLEX/superflex slot eligibility and is the true maximum (a
      greedy slot-fill that mis-handles overlapping flex slots would under-count).
- [ ] The chip renders for everyone, with no subscription gating (including when `billing` is off).
- [ ] A box score with no bench data (e.g. ESPN before 2018) shows no chip.
- [ ] A perfect lineup shows 100% and the perfect-lineup dialog state.

## Sources
`src/features/lineup_efficiency/` (`compute-lineup-efficiency.ts`,
`lineup-efficiency-chip.tsx`), `src/components/box-score-card.tsx`,
`src/lib/position-constants.ts` (`POS_NORMALIZE`).
