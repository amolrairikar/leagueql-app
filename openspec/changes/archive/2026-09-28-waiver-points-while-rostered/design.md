# Design

## Context

`rosPointsFor(playerId, week, weekly)` sums a player's box-score points for every week `>= week`.
`netPickupValue` (`transaction-impact.ts`) uses it for both adds and drops, and the cards and Top
transactions share it. The page already loads the full season's transactions.

## Goals / Non-Goals

**Goals:**
- An added (waiver/FA) or acquired (trade) player stops counting once he leaves that roster.

**Non-Goals:**
- Changing dropped-player windows (waiver/FA drops keep full rest of season).
- Detecting roster presence from box scores.

## Decisions

- **Stint end = next drop transaction, not box-score presence.** A waiver's `week` usually names
  the upcoming week, so a weekly roster snapshot can miss the add week and zero out a legitimate
  pickup. The transaction list is exact: the stint ends at the week of the first later (by
  `created`) transaction, of any type, whose `drops` remove that player from that roster. That
  week is excluded, matching the page's existing convention that a transaction's week belongs to
  the new owner.
- **Index once.** `buildRosterExits(transactions)` maps `${rosterId}:${playerId}` → drops sorted by
  `created`; `exitWeek` picks the first after the add. Built from the full season list (not the
  filtered wire), so a re-drop of any type is seen.
- **`rosPointsFor` gains an exclusive `untilWeek` defaulting to `Infinity`**, keeping existing
  callers unchanged.
- **Dropped players keep full rest of season** (product decision).
- **Trades reuse the same bound.** `sideTotal` bounds each acquired player by `exitWeek` on the
  receiving roster; a trade's own drops are keyed to the sending roster and precede nothing
  (`created > txn.created`), so they never cut the receiver's stint.

## Risks / Trade-offs

- Onboarded history must include the re-drop; ESPN only has transactions from 2026 onward, but a
  pickup and its re-drop are in the same season, so both are present or both are absent.
