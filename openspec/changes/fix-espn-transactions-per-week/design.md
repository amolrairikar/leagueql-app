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

- **Iterate the full `matchup_weeks(season)` range rather than bounding by the current scoring period.** Matchups already do this and rely on ESPN returning empty for unplayed weeks; transactions behave the same way. This avoids threading the current scoring period (available in `_resolve_active_seasons`'s status fetch as `latestScoringPeriod`) through into `_build_all_request_urls`, keeping the two fan-outs symmetric and the code simple. Trade-off: a handful of extra empty requests for future weeks — the same cost matchups already pay.
- **Tag per-week transaction URLs `transactions_week{N}` and add `scoringPeriodId` in `_construct_request_url`.** Reuses the exact matchup convention. The `_ESPN_DATA_FILTERS` lookup must resolve the `transactions_week{N}` data_type to the transactions filter (e.g. strip the `_week{N}` suffix before lookup, as matchups already do), since `_filter_transactions` ignores the `data_type`/`season` args.
- **Change the processor's ESPN collector to `data_type.startswith("transactions")`.** Matches the Sleeper path and lets all per-week payloads flow into `raw_transactions`, which is then compiled and chunked exactly as today.

## Risks / Trade-offs

- [More ESPN API calls per onboard/refresh — one per week for the latest season] → Bounded by the season length (≤18), runs under the existing concurrency semaphore, and mirrors matchups which already fan out identically; negligible added load.
- [A `transactions_week{N}` data_type not resolving in `_ESPN_DATA_FILTERS`, causing dropped payloads] → Covered by unit tests asserting the filter is applied to per-week transaction responses and by a component test asserting multi-week transactions all land in the view.
- [Duplicate transactions if a transaction appears under more than one scoring period] → ESPN scopes each transaction to a single `scoringPeriodId`, so per-week requests partition the season without overlap; the compile step keys on `transaction_id` shape already produced today.
