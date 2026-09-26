## 1. ESPN client: fan transactions out per week

- [x] 1.1 In `_construct_request_url` (`src/onboarder/espn_client.py`), add `scoringPeriodId` to the query for per-week transaction requests (data_type prefixed `transactions_week`), mirroring matchups; verify with a unit test asserting the built URL contains the expected `scoringPeriodId` and `view=mTransactions2`.
- [x] 1.2 In `_build_all_request_urls`, for the latest season loop `matchup_weeks(season)` for transactions, appending `(season, f"transactions_week{week}", url)`; still skip transactions for non-latest seasons; verify with a unit test asserting one transactions URL per week for the latest season and none for earlier seasons.
- [x] 1.3 Ensure the `_ESPN_DATA_FILTERS` lookup resolves `transactions_week{N}` to `_filter_transactions` (strip the `_week{N}` suffix as matchups do); verify with a unit test that a per-week transactions response is filtered to EXECUTED waiver/free-agent items.
- [x] 1.4 Bound the per-week transaction fetch at the current scoring period: capture `status.latestScoringPeriod` in `_get_league_seasons` and iterate `range(1, current + 1)` for transactions (falling back to the full week range when unknown), because ESPN returns the current period's transactions for any `scoringPeriodId` at or beyond it. Verify with unit tests asserting the capped week count and the fallback.

## 2. Processor: collect all per-week transaction payloads

- [x] 2.1 In `src/processor/handler.py`, change the ESPN transaction collector (~line 986) from `item["data_type"] == "transactions"` to `item["data_type"].startswith("transactions")`; verify with a unit test that transaction records from multiple `transactions_week{N}` items are all appended to `raw_transactions`.
- [x] 2.2 Dedupe transactions by `(season, id)` in `compile_espn_transactions` so a transaction returned by more than one per-week request is stored once; verify with a unit test that a duplicated transaction id across weeks yields a single row, and an end-to-end component scenario asserting an echoed transaction does not duplicate.

## 3. Spec sync

- [x] 3.1 Confirm the delta in `specs/backend/espn-transactions/spec.md` matches the implemented behavior and run `openspec validate fix-espn-transactions-per-week --strict` with no errors.

## 4. Tests across tiers

- [x] 4.1 Add/extend backend unit tests (`tests/unit/onboarder`, `tests/unit/processor`) for the per-week URL fan-out, filter resolution, and multi-week collection; verify `pipenv run pytest tests/unit` passes with coverage near 100% including the new paths.
- [x] 4.2 Add/extend a backend component test (`tests/component`) that fetches an ESPN league whose latest season has transactions across multiple weeks and asserts the `TRANSACTIONS#{season}` view contains rows from every week; verify `pipenv run behave tests/component` passes.

## 5. Lint & format

- [x] 5.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`; verify both report clean.
