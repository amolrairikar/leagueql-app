## Why

Transactions (waivers and free-agent adds/drops) are currently a Sleeper-only feature end-to-end; ESPN leagues see no `/transactions` page and store no transaction data. ESPN exposes usable current-season transaction data via its `mTransactions2` view, so we can give ESPN users the same activity view Sleeper users already have.

## What Changes

- Fetch ESPN transactions from `...?view=mTransactions2` for the **current (latest) season only** (past seasons return no data on this endpoint) during onboarding/refresh.
- Keep only **EXECUTED** transactions of type **FREEAGENT** (→ `free_agent`) and **WAIVER** (→ `waiver`). Skip DRAFT, ROSTER (lineup swaps), and all trade types for now.
- Compile ESPN transactions into the existing precomputed `transactions` view (player IDs resolved to names/positions, team IDs resolved to team labels), reusing the Sleeper row shape with `draft_picks` always empty. Write them as chunked `TRANSACTIONS#{season}` DynamoDB items and serve them through the existing `queryType=TRANSACTIONS#{season}` API.
- Surface ESPN transactions in the existing `/transactions` UI: show the nav item for ESPN leagues and make the type filter platform-aware (ESPN: Waivers + Free Agents; no Trades).

## Capabilities

### New Capabilities
- `backend/espn-transactions`: Build a precomputed transactions view for ESPN leagues from the `mTransactions2` view — current-season EXECUTED waivers and free-agent adds/drops, with players/teams resolved — written to DynamoDB and served through the query API.

### Modified Capabilities
- `backend/sleeper-transactions`: The "No item for empty transactions" requirement currently asserts ESPN leagues never produce a `TRANSACTIONS` item; that exclusion is removed now that ESPN writes them.
- `frontend/transactions`: The `/transactions` page and nav are no longer Sleeper-only — the nav item shows for ESPN too and the type filter is platform-aware (ESPN offers only Waivers and Free Agents).

## Impact

- Backend: `src/onboarder/espn_client.py` (new `transactions` fetch type + filter, current-season-only URL), `src/processor/handler.py` (ESPN transaction compile + team map, relaxed write guard), `src/processor/queries.py` (ESPN `TRANSACTIONS` query). Docs: `docs/db/dynamodb_spec.md`.
- Frontend: `frontend/src/features/sidebar/app-sidebar.tsx` (nav gating), `frontend/src/features/transactions/transactions.tsx` (platform-aware filters/summary), plus comment-only updates to `frontend/src/components/api/types.ts` and `frontend/src/features/transactions/api-calls.ts`.
- New DynamoDB items: `TRANSACTIONS#{season}` for ESPN leagues (current season only). No new deployed component; reuses the existing onboarder → processor chain and query API.
- Tests: backend unit + component, frontend component (transactions + sidebar nav gating).
