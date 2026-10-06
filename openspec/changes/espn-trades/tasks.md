# Tasks

## 1. Backend

- [x] 1.1 Keep EXECUTED `TRADE_UPHOLD`/`TRADE_ACCEPT` records and `TRADE` items in `_filter_transactions` (`src/onboarder/espn_client.py`); verify with unit tests that `TRADE_PROPOSAL`, a pending accept, and a cancelled proposal are dropped
- [x] 1.2 Map both types to `trade` in `compile_espn_transactions` (`src/processor/handler.py`), resolving `TRADE` items into drop + add, taking `roster_ids`/`teams` from the items, and collapsing an accept + uphold pair into one row; verify with unit tests
- [x] 1.3 Update `docs/db/dynamodb_spec.md` and the comment in `src/processor/queries.py`
- [x] 1.4 Add the trade records to the ESPN component-test fixture and assert one `trade` row from the query API

## 2. Frontend

- [x] 2.1 Remove the ESPN trade gating in `frontend/src/features/transactions/transactions.tsx` (filter, default, summary column)
- [x] 2.2 Update the ESPN scenarios in `transactions.feature` and their steps

## 3. Specs

- [ ] 3.1 Update the `frontend/transactions` Purpose wording at archive time (ESPN now has trades)
