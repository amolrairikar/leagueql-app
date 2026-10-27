# Tasks

## 1. Verify identifiers

- [x] 1.1 Confirm MATCHUPS `team_a_id`/`team_b_id` equal transaction `roster_id` for ESPN, Sleeper and Yahoo (`src/processor/queries.py`, `handler.py`); record the finding, and if they differ add a mapping before continuing

## 2. Roster-scoped points

- [x] 2.1 Add a roster-keyed weekly points index and a windowed lookup in `frontend/src/features/transactions/api-calls.ts`; verify with `npm run build:ci`
- [x] 2.2 Use it for the added side of `netPickupValue` in `transaction-impact.ts` (trades untouched) and thread the index through `transactionImpact`/`topTransactions`; verify existing top-transaction scenarios still pass
- [x] 2.3 Build the index in `transactions.tsx` and use it for waiver/FA add rows and the net footer in `TeamPanel`; verify by running the transactions tests
- [x] 2.4 Add scenarios to `__tests__/transactions.feature` and steps in `transactions.steps.test.tsx` for "not in the roster's lineup" and "scores for another roster"; fix any existing fixtures that place players on the wrong team; verify `npx vitest run src/features/transactions` passes

## 3. Quality checks

- [x] 3.1 Run `npm run format:fix`, `npm run lint`, and `npm run build:ci` in `frontend/` and verify they pass
- [x] 3.2 Run `npx @fission-ai/openspec@latest validate --all` and verify it passes

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
