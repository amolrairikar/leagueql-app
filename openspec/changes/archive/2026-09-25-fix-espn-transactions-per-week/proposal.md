## Why

ESPN's `mTransactions2` view, when requested without a `scoringPeriodId`, returns only the **current** scoring period's transactions — not the whole season. The ESPN client issues a single such request per league, so a league only ever stores the transactions from the week that was current at fetch time (e.g. a league onboarded in week 1 shows only week-1 transactions, and every later week is silently missing). This makes the ESPN transactions view materially incomplete for any league fetched after week 1.

## What Changes

- Expand ESPN transaction fetching per scoring period, exactly like matchups: for the latest season, issue one `mTransactions2` request per week over `matchup_weeks(season)`, each carrying that week's `scoringPeriodId`, tagged `transactions_week{N}`. Unplayed future weeks return empty and are harmless (same as matchups).
- Update the processor's ESPN path to collect transaction items by `data_type.startswith("transactions")` (matching the Sleeper path) instead of an exact `== "transactions"` match, so all per-week transaction payloads are combined into the season's view.
- Revise the `backend/espn-transactions` spec requirement that states transactions are fetched "in a single request per league" and that a single call returns the whole season — replace it with per-scoring-period fetching for the current season.
- No change to the stored row shape, the DynamoDB item layout (`TRANSACTIONS#{season}#{chunk}`), or the query API contract; only the completeness of the fetched data changes.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `backend/espn-transactions`: The "Fetch ESPN transactions for the current season only" requirement changes from a single per-league request to one request per scoring period (week) of the latest season, combined into the season's view. Earlier seasons are still not requested.

## Impact

- Code: `src/onboarder/espn_client.py` (`_build_all_request_urls`, `_construct_request_url`, `_ESPN_DATA_FILTERS` lookup for `transactions_week{N}`), `src/processor/handler.py` (ESPN transaction collection prefix match).
- Spec: `openspec/specs/backend/espn-transactions/spec.md`.
- Tests: backend unit (`tests/unit/onboarder`, `tests/unit/processor`) and backend component (`tests/component`) covering ESPN transactions.
- No API contract, DynamoDB schema, frontend, or infrastructure changes. Slightly more ESPN API calls per onboard/refresh (one per week for the latest season), mirroring existing matchup fan-out.
