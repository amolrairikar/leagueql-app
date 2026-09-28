# Proposal

## Why

A waiver or free-agent pickup's net value counts the added player's points from the pickup week to
the end of the season, even after the team cut or traded him — so a team gets credit for points
scored on someone else's roster (or on waivers). That inflates net pickup values and the Top
transactions ranking built on them.

## What Changes

- An added player's points on a waiver/free-agent move count only while on the acquiring roster:
  from the move's week up to (not including) the week of the next season transaction of any type
  that drops him from that roster.
- Dropped players are unchanged (full rest of season).
- The waiver/free-agent points column header changes from "Rest of season points" to "Points while
  rostered"; the Top transactions "Ranked by rest-of-season points gained" caption is removed.
- Two-team trades get the same bound: each acquired player counts only while on the receiving
  roster, so side totals, the winner, and the margin reflect only points the team actually kept.
  The trade side-total footer label changes from "Rest-of-season pts" to "Points while rostered".
- Top transactions follows automatically (it ranks by net pickup value and trade margin).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/transactions`: the "Waiver and free-agent rest-of-season points" and "Trade
  rest-of-season points" requirements bound acquired players to their stint on the acquiring
  roster.

## Impact

- **Frontend**: `frontend/src/features/transactions/api-calls.ts` (`rosPointsFor` upper bound),
  `transaction-impact.ts` (roster-exit index, `netPickupValue`), `transactions.tsx`,
  `top-transactions.tsx`; component tests in `__tests__/transactions.feature` + steps.
- No backend, API, DynamoDB, or infrastructure change.
