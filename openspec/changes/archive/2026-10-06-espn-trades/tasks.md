# Tasks

## 1. Backend

- [x] 1.1 Keep EXECUTED `TRADE_UPHOLD`/`TRADE_ACCEPT` records and `TRADE` items in `_filter_transactions` (`src/onboarder/espn_client.py`); verify with unit tests that `TRADE_PROPOSAL`, a pending accept, and a cancelled proposal are dropped
- [x] 1.2 Map both types to `trade` in `compile_espn_transactions` (`src/processor/handler.py`), resolving `TRADE` items into drop + add and taking `roster_ids`/`teams` from the items; verify with unit tests
- [x] 1.3 Update `docs/db/dynamodb_spec.md` and the comment in `src/processor/queries.py`
- [x] 1.4 Add the trade records to the ESPN component-test fixture and assert one `trade` row from the query API
- [x] 1.5 Keep `relatedTransactionId` and `acceptedDate` in `_filter_transactions`, and add the player-card step to `ESPNClient.fetch_all` (hidden-trade detection, candidate IDs from weeks N and N+1 rosters, 40-ID `kona_playercard` batches, best executed accept per key, `transactions_trade_cards` result, failures logged and tolerated); verify with unit tests for each of those behaviors and for no card requests when no trade is hidden
- [x] 1.6 Group trade records in `compile_espn_transactions` by `relatedTransactionId` (falling back to `id`, and to the content key for unlinked records), take traded players and accept-time drops from the group, pick the uphold as the row record with `processDate`/`acceptedDate`/`proposedDate`, and skip groups with no traded players; verify with unit tests for the 2026 shape (empty uphold + card accept), the 2018 shape, an accept-only trade, and an unrecoverable trade
- [x] 1.7 Add a 2026-style hidden trade (an uphold with no items plus a `transactions_trade_cards` accept) to the ESPN component fixture and assert it returns as one `trade` row with both teams
- [x] 1.8 Update `docs/db/dynamodb_spec.md` for card-recovered trades; confirm no architecture diagram change is needed (no new deployed component)
- [x] 1.9 Confirm the `kona_playercard` response shape against a live league with a hidden trade before release

## 2. Frontend

- [x] 2.1 Remove the ESPN trade gating in `frontend/src/features/transactions/transactions.tsx` (filter, default, summary column)
- [x] 2.2 Update the ESPN scenarios in `transactions.feature` and their steps

## 3. Specs

- [x] 3.1 Update the `frontend/transactions` Purpose wording at archive time (ESPN now has trades)
