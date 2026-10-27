# Design

## Context

Net pickup value is computed client-side in `transaction-impact.ts` from `buildWeeklyPlayerPoints`
(`api-calls.ts`), a `player → week → points` index that discards which team's lineup a player was
in. `pointsWhileRostered` is shared by waiver/FA adds and trade side totals. Each `MatchupItem`
carries `team_a_id`/`team_b_id` plus per-team `*_starters` and `*_bench` lists. See proposal.md.

## Goals / Non-Goals

**Goals:**
- Waiver/FA added-player points count only weeks the player is in the acquiring roster's lineup.

**Non-Goals:**
- Changing the dropped side, trade totals, or the exit-week window logic.
- Any backend or data change.

## Decisions

- **Separate roster-keyed index** (`${team_id}:${player_id}` → week → points) built alongside the
  existing index, rather than changing `buildWeeklyPlayerPoints`. The existing index still serves
  the dropped side (follows the player across rosters) and trades, which must stay unchanged.
- **New added-side function for waiver/FA** used by `netPickupValue` and the waiver/FA rows in
  `TeamPanel`; `pointsWhileRostered`/`sideTotal` stay as-is for trades. Alternative (change the
  shared function) rejected: it would alter trade totals against the agreed scope.
- Keep the existing exit-week window; the roster index only filters which weeks inside it count.

## Risks / Trade-offs

- [MATCHUPS `team_*_id` may not equal a transaction's `roster_id` on some platform] → verify for
  ESPN, Sleeper and Yahoo before implementing; if they differ, map through team data.
- [Waiver/FA and trade rows for the same player on one card now use different logic] → accepted by
  scope; documented in code comments.
