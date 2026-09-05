## Context

See proposal.md — Why. The relevant current state:

- `dataframe_to_dynamo_items` (`src/processor/handler.py`) groups all rows for a sort key into one item `{PK, SK, data: [rows...]}`. `KeySchema` (`pk`, `sk`, `entity_type`) drives PK/SK construction. Every precomputed view shares this one path.
- `TRANSACTIONS_SCHEMA` maps a row to `TRANSACTIONS#{season}`. Transactions are the only view with unbounded rows-per-partition; all other views are a handful of rows per season/week.
- The query handler (`src/api/routes.py`) parses `queryType` into `base#suffix`, builds `sk`, and branches: an SK ending in `#` (no suffix) runs a paginated `begins_with` query concatenating each item's `data`; otherwise it runs an exact `get_item`. The frontend calls `TRANSACTIONS#{season}` (suffixed), which today lands in the `get_item` branch.
- DynamoDB caps an item at 400 KB (PK + SK + attribute names + values). `batch_writer` surfaces an oversized item as `ValidationException`.

## Goals / Non-Goals

**Goals:**
- Store an arbitrarily large season's transactions without exceeding the per-item limit.
- Keep every other view's on-disk shape and the frontend contract unchanged.
- Backward compatibility: leagues already written with a single `TRANSACTIONS#{season}` item keep resolving until refreshed.

**Non-Goals:**
- Chunking any view other than transactions.
- Changing the transaction row shape, resolution logic, or the API request/response contract.
- Migrating existing data eagerly — the existing `reprocess_all` backfill path rewrites into the chunked shape when a league is refreshed.

## Decisions

### Decision: Chunk on serialized size, not a fixed row count
Split a sort key's rows into chunks bounded by measured serialized size rather than a fixed N-per-chunk. Transaction rows vary widely (a bare free-agent add vs. a multi-player, multi-pick trade), so a row count either wastes space or risks a fat chunk still overflowing.

- **Cap:** target ~300 KB per item (raw `data` payload), leaving headroom under 400 KB for the PK/SK strings, attribute names, and DynamoDB's numeric/string encoding overhead. A single row larger than the cap is highly implausible for this data, but the splitter still emits it as its own chunk (a chunk is never empty) rather than looping — DynamoDB would then reject that one row, which is the correct, visible failure.
- **Measurement:** size each sanitized row once (e.g. `len(json.dumps(row, default=str))` as a proxy for the item's contribution) and accumulate; start a new chunk when adding the next row would cross the cap. Approximate-but-conservative sizing is fine because the cap already carries headroom.
- **Alternative rejected:** fixed rows-per-chunk — simpler but not robust to row-size variance.

### Decision: Opt-in chunking per `KeySchema`, default off
Add a flag to `KeySchema` (e.g. `chunked: bool = False`) and set it only on `TRANSACTIONS_SCHEMA`. `dataframe_to_dynamo_items` chunks only when the schema opts in; every other schema keeps emitting exactly one item per sort key, byte-for-byte as today.

- **Chunk SK:** `f"{sk}#{index:04d}"`, zero-padded so lexical sort order matches numeric order and the `begins_with` read returns chunks in order. Four digits is far more than any season will need.
- **Alternative rejected:** always append a chunk index to every view's SK — needless churn to unrelated views and their reads/specs.
- **Alternative rejected:** one item per transaction (`TRANSACTIONS#{season}#{transaction_id}`) — multiplies item count and read RCUs with no benefit; the view is always read whole.

### Decision: Read transactions via a prefix query that also matches legacy keys
Route a suffixed transactions query through the paginated `begins_with` branch instead of `get_item`, using prefix `TRANSACTIONS#{season}` (no trailing `#`).

- Matching without a trailing `#` covers both the new `TRANSACTIONS#{season}#{chunk}` items and any legacy `TRANSACTIONS#{season}` item, so onboarded leagues keep resolving before they are reprocessed.
- Prefix collision is impossible: seasons are distinct 4-digit years, so `TRANSACTIONS#2024` is never a prefix of another season's key.
- Implementation shape: the handler already has both branches; the change makes the transactions base type select the prefix branch even when a suffix is present. Keep it narrow — only transactions changes; all other suffixed views keep `get_item`.
- The existing branch already paginates `LastEvaluatedKey` and concatenates `data`, so no new read machinery is needed.

### Decision: Delete the legacy bare `TRANSACTIONS#{season}` item when writing chunks
The processor has **no** delete/prune step today — a refresh/reprocess only overwrites items via `put_item`. So a league first onboarded under the old code carries a bare `TRANSACTIONS#{season}` item that a reprocess would never remove; it would then coexist with the new `TRANSACTIONS#{season}#{chunk}` items, and the backward-compatible prefix read (which matches both) would return the season's rows twice.

To prevent that, the chunked write path SHALL delete any pre-existing bare `TRANSACTIONS#{season}` item for each season it writes, **before** writing that season's chunks. After a reprocess a season holds only chunk items; the bare-key match in the prefix read then serves **only** not-yet-reprocessed leagues, and never duplicates.

- **Scope — only the reprocessed seasons:** the processor loads raw data and writes items only for `seasons_to_process` (initial onboard → all seasons; a new season → just the new one; an in-season refresh → only the last season). So the delete fires only for the seasons actually rewritten in that run; every other season's items — including old-format bare `TRANSACTIONS#{season}` items — are left untouched and keep resolving through the backward-compatible prefix read. Old-format seasons migrate lazily, as they happen to be the last-season of an in-season refresh, or all at once via the `reprocess_all` backfill.
- **Delete-before-write ordering:** deleting the bare key first means a mid-run crash leaves the season temporarily short (repaired by the next idempotent run, and the run is marked FAILED regardless) rather than leaving a bare item and chunks coexisting, which would duplicate rows on read until the next run. Writing chunks first and deleting after would open exactly that transient-duplication window.

- **Alternative rejected:** read with a trailing `#` (`TRANSACTIONS#{season}#`) so only chunks match — avoids the delete, but drops backward compatibility, 404-ing every onboarded league until it is reprocessed. The delete keeps existing leagues working through the transition.
- **Alternative rejected:** dedupe rows on read — hides the stale item, adds per-request cost, and needs a stable row identity; deleting at the source is cleaner.
- Scope: the delete targets only the bare `TRANSACTIONS#{season}` key. It does not need to reconcile a shrinking chunk count across reprocesses, because a season's chunk count only grows (transactions are append-only within a season); if a later concern makes chunk counts shrink, stale high-index chunks would need pruning too, but that is out of scope here.

## Risks / Trade-offs

- **[Stale bare key duplicates rows on read]** A reprocessed legacy league keeps its bare `TRANSACTIONS#{season}` item unless the writer deletes it, and the prefix read would then double the season. → Writer deletes the bare key when writing chunks (see Decision above). Covered by a component test that reprocesses a previously single-item season and asserts no duplication.
- **[Read now always multi-item for transactions]** A season that fits one chunk still costs a `query` instead of a `get_item` (marginally higher latency/RCU). → Negligible; transactions is a low-frequency, cache-friendly (`max-age=300`) view.
- **[Undersized cap wastes items; oversized cap overflows]** → The 300 KB cap is deliberately conservative; a unit test asserts each emitted chunk's payload stays under the cap for a synthetic large season.

## Migration Plan

1. Deploy processor + API together or in either order — the API prefix read is backward-compatible with existing single-key items, and the processor only changes what new writes look like.
2. Re-run the existing `reprocess_all` Sleeper backfill (already specced under `backend/sleeper-transactions`) to rewrite every league's transactions into the chunked shape; leagues that currently fail onboarding will then succeed.
3. Rollback: revert the processor to single-item writes. The API prefix read still resolves single-key items, so a rollback is safe as long as no chunked-only data is required; already-chunked leagues would need a reprocess after rollback (acceptable, low volume).
