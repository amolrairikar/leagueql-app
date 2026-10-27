# Design

## Context

`export_league` first resolves the league, authorizes, validates seasons and reads the single
`TEAMS` item, then loops `selected_seasons × EXPORT_SEASON_VIEWS` calling `read_view` serially.
`read_view` is synchronous, uses the module-level boto3 `main.table` resource, and converts
`ClientError` into an `HTTPException(500, "Failed to retrieve league data")`. The API runs on a
2048 MB Lambda (15 s timeout) with botocore instrumented for OTel (`common/tracing.py`). See
proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Cut export wall-clock from roughly (reads × latency) to roughly (reads / workers × latency).
- Identical response body, status codes, and headers for successful requests.

**Non-Goals:**
- Changing `read_view` (also used by the query endpoint) or the data layout.
- Merging reads into a single per-season `begins_with` query; it would change the shape of the
  read path, and the boto3 resource layer would still deserialize every item.
- Parallelizing `/query` or other endpoints.

## Decisions

- **`ThreadPoolExecutor` with a bounded `max_workers` (8).** The work is I/O bound and boto3 is
  synchronous, so threads fit. boto3 low-level clients are thread-safe, and `Table` resources used
  only for read operations like these are safe to share across threads in practice. Alternative:
  `asyncio` with an async client; rejected as a far larger change for one endpoint. 8 keeps
  concurrency below DynamoDB's connection pool default (10) so no worker waits on a pooled
  connection.
- **Submit all `(season, view)` reads, then assemble in the original loop order.** Futures are
  kept in a list in the same order the serial loop used and results are read back by iterating
  that list, so the bundle structure and key order are deterministic whatever order reads finish
  in. This is what the "Deterministic export bundle" requirement pins down.
- **Errors propagate unchanged.** `future.result()` re-raises the `HTTPException` from `read_view`,
  failing the request with the same `500`. Remaining queued reads are cancelled by leaving the
  `with` block via the exception (`shutdown(cancel_futures=True)`); no partial bundle is built.
- **Propagate trace context into workers.** Threads do not inherit `contextvars`, so each task runs
  under `contextvars.copy_context().run(...)`; DynamoDB spans then parent to the request span
  instead of starting orphaned traces (backend/otel-tracing).
- **Keep the `TEAMS` read inline** before the fan-out; it is one call and the per-season filter
  depends on it.

## Risks / Trade-offs

- [Burst of parallel reads could throttle a small on-demand table] → on-demand capacity absorbs
  the burst, total RCUs are unchanged, and the worker cap bounds concurrency; boto3's default
  retries handle throttles.
- [Shared `Table` resource across threads] → used for read-only calls, and unit/component tests
  exercise concurrent use; fall back to per-thread resources if a problem shows up.
- [Memory: all views held at once] → already true of the serial implementation (the whole bundle
  is built before responding).
- [Harder to debug than serial code] → the assembly order and error behavior are pinned by tests.
