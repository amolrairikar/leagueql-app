# Proposal

## Why

A waiver / free-agent move's net pickup value credits the added player with every point they scored
in the transaction-week-to-exit-week window, taken from a player+week index that ignores which team
the player was on. A week in which the player was not actually in the acquiring team's starters or
bench (or was listed on another team) still counts, overstating the pickup.

## What Changes

- For waiver / free-agent moves on `/transactions`, an added player's "Points while rostered" and
  the net pickup value count only weeks in which the player appears in the acquiring roster's
  starters or bench in that week's `MATCHUPS` box score, within the existing window.
- Dropped-player totals (rest of season) are unchanged.
- Trade side totals and winning margins are unchanged.
- The Top transactions ranking inherits the new value for waiver / free-agent moves.

## Capabilities

### New Capabilities

### Modified Capabilities
- `frontend/transactions`: the "Waiver and free-agent rest-of-season points" requirement now scopes
  the added player's points to weeks they were in the acquiring roster's lineup.

## Impact

- Frontend only: `frontend/src/features/transactions/` (`api-calls.ts`, `transaction-impact.ts`,
  `transactions.tsx`) and its jest-cucumber tests.
- No backend, API contract, or data model changes.
