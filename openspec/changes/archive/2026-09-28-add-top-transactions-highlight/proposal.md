# Proposal

## Why

The `/transactions` page lists every move of the season and already computes how much each one was
worth (a waiver/free-agent move's net pickup value, a two-team trade's winning margin), but nothing
surfaces which moves actually mattered — the standouts are buried in a long, type-filtered wire.

## What Changes

- Add a "Top transactions" section near the top of `/transactions` (below the season selector /
  ESPN disclaimer, above the Summary table) showing the season's five highest-impact moves as a row
  of stat tiles, across waivers, free agents, and trades together.
- Impact reuses the existing rest-of-season math: a waiver/free-agent move's net pickup value, and a
  two-team trade's winning margin (credited to the winning team). Only moves with a positive impact
  are eligible; ties break by the earlier transaction.
- The section ignores the type filter, and is hidden when there is nothing eligible or the season's
  matchup box scores are unavailable.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/transactions`: adds the "Highlight the season's top transactions" requirement.

## Impact

- **Frontend**: `frontend/src/features/transactions/transactions.tsx` (render the section, reuse
  extracted helpers), new `transaction-impact.ts` (pure ranking helpers + the ROS math moved out of
  the page), new `top-transactions.tsx` (tile component), new `type-meta.ts` (shared type chips);
  component tests in `__tests__/transactions.feature` + steps.
- No backend, API contract, DynamoDB schema, or infrastructure change — the page already loads the
  season's `MATCHUPS` box scores.
