## Context

See proposal.md — Why. The ESPN client (`src/onboarder/espn_client.py`) already fans matchups out per week: `_build_all_request_urls` loops `matchup_weeks(season)`, tagging each URL `matchups_week{N}`, and `_construct_request_url` adds `scoringPeriodId` for matchups. Transactions currently use a single untagged `transactions` request with no `scoringPeriodId`, which ESPN answers with only the current scoring period. The processor collects ESPN transaction items with an exact `data_type == "transactions"` match (`handler.py:986`), whereas the Sleeper path already uses `data_type.startswith("transactions")` (`handler.py:1677`).

## Goals / Non-Goals

**Goals:**
- Capture every completed ESPN waiver/free-agent transaction for the latest season, across all weeks, by mirroring the matchup per-week fan-out.
- Keep the stored row shape, DynamoDB item layout, and query API contract unchanged.

**Non-Goals:**
- Fetching transactions for earlier (non-latest) seasons — still explicitly excluded (ESPN returns none for them).
- Any change to Sleeper or Yahoo transaction handling.
- Optimizing the number of ESPN calls beyond matching the existing matchup pattern.

## Decisions

- **Bound the per-week transaction fetch at the current scoring period, unlike matchups.** ESPN's `mTransactions2` does NOT behave like matchups for future weeks: a request for any `scoringPeriodId` at or beyond the current period returns the *current* period's transactions rather than an empty set. Iterating the full `matchup_weeks` range therefore returns the current week's transactions once per future week (e.g. weeks 3–18 each echo week 3 → 16× duplication). We capture `status.latestScoringPeriod` in `_get_league_seasons` (which already does a status fetch) and iterate `range(1, current + 1)` for transactions; matchups keep the full range. When the current period is unavailable, we fall back to the full range and rely on dedup.
- **Dedupe transactions by `(season, id)` in `compile_espn_transactions`.** Defense-in-depth so correctness does not depend on the cap being exact: if ESPN echoes a transaction across weeks (or the cap is off), each transaction is still stored exactly once. Cheap (a `set`), and it keeps the full-range fallback correct.
- **Tag per-week transaction URLs `transactions_week{N}` and add `scoringPeriodId` in `_construct_request_url`.** Reuses the matchup convention. `_process_api_results` resolves the `transactions_week{N}` data_type to `_filter_transactions` via a `startswith` branch (mirroring matchups), since `_filter_transactions` ignores the `data_type`/`season` args.
- **Change the processor's ESPN collector to `data_type.startswith("transactions")`.** Matches the Sleeper path and lets all per-week payloads flow into `raw_transactions`, which is then compiled (with dedup) and chunked exactly as today.

## Risks / Trade-offs

- [ESPN returns the current period's transactions for future-week requests, duplicating data] → Cap the fetch at the current scoring period AND dedupe by `(season, id)` at compile time; covered by unit tests (cap + fallback + dedup) and an end-to-end component scenario asserting an echoed transaction yields one row.
- [`status.latestScoringPeriod` absent (e.g. a not-yet-started season)] → `latest_scoring_period` defaults to `None`; `_build_all_request_urls` falls back to the full week range and the compile-time dedup keeps each transaction once.
- [More ESPN API calls per onboard/refresh — one per week up to the current period] → Bounded by the current scoring period (≤18), runs under the existing concurrency semaphore; strictly fewer calls than the full-range approach.
