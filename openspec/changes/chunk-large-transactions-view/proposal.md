## Why

The processor packs every transaction row for a Sleeper season into a single `TRANSACTIONS#{season}` DynamoDB item's `data` list. An active dynasty league's season exceeds DynamoDB's hard **400 KB per-item limit**, so `batch_writer` raises `ValidationException: Item size has exceeded the maximum allowed size` and the whole processing run fails — the league never finishes onboarding. Transactions are the only high-cardinality-per-partition view, so no other view hits this.

## What Changes

- The processor SHALL split a season's transaction rows across multiple size-bounded items keyed by a chunk index: `TRANSACTIONS#{season}#{chunk:04d}`. Each item stays under a safe cap (well below 400 KB), so an arbitrarily active season can be stored.
- The chunking SHALL be opt-in per view (only transactions), leaving every other precomputed view's single-item shape unchanged.
- **BREAKING** (storage shape only, internal): the transactions view no longer writes a bare `TRANSACTIONS#{season}` item — it writes `TRANSACTIONS#{season}#{chunk}` items, and the writer deletes any pre-existing bare `TRANSACTIONS#{season}` item for each season it rewrites (the processor has no prune step today, so this prevents a stale bare item from coexisting with chunks and duplicating rows on read). Legacy single-key items from not-yet-reprocessed leagues remain readable until the league is refreshed/reprocessed (see Impact).
- The query API SHALL serve a season-suffixed `TRANSACTIONS#{season}` query with a paginated `begins_with` prefix scan that concatenates the chunks' `data`, instead of an exact `get_item`. The prefix is chosen so it matches both new chunked items and any legacy single-key item, preserving backward compatibility.
- No frontend change: `getTransactions` keeps calling `queryType=TRANSACTIONS#{season}` and receives the same flat row list.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `backend/sleeper-transactions`: the view is now written as multiple chunked `TRANSACTIONS#{season}#{chunk}` items instead of one `TRANSACTIONS#{season}` item, so a season's rows can exceed the DynamoDB per-item size limit.
- `backend/query-precomputed-views`: a season-suffixed `TRANSACTIONS` query is served via a paginated prefix query that concatenates chunk items, rather than the exact `get_item` used for other suffixed views.

## Impact

- **Code:** `src/processor/handler.py` — `KeySchema` (add a chunking opt-in), `dataframe_to_dynamo_items` (size-bounded chunk splitting), the `TRANSACTIONS_SCHEMA` wiring. `src/api/routes.py` — the `query` handler's suffixed-vs-prefix branch for transactions.
- **Docs:** `docs/db/dynamodb_spec.md` — describe the chunked `TRANSACTIONS#{season}#{chunk}` item shape. `docs/api/openapi_spec.yaml` — no contract change (same request/response), verify only.
- **Tests:** backend unit (`tests/unit/processor` — chunk splitting boundaries and the single-chunk case; `tests/unit/api` — prefix read + concatenation for transactions), backend component (`tests/component` — a large-transactions season round-trips onboarding→query without error). No frontend behavior change, so frontend tests are unaffected (verify the existing transactions scenarios still pass).
- **Data migration:** existing large leagues that already failed remain broken until re-onboarded/reprocessed; leagues that succeeded keep working via the backward-compatible prefix. The existing `reprocess_all` backfill path rewrites transactions into the chunked shape.
- **Deploy order:** the API read change (prefix query that also matches legacy keys) is backward-compatible with old single-key items, so processor and API can deploy independently in either order.
