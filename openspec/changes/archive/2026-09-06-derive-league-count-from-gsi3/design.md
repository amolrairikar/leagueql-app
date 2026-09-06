## Context

See proposal.md — Why. The `sync-counts` worker already holds the DynamoDB client, static AWS
credentials (Worker secrets), the `DYNAMODB_TABLE`/`AWS_REGION` vars, and the `COUNTS_KV` binding,
and runs hourly via cron. GSI3 already indexes exactly the league `METADATA` items
(`HASH = SK = "METADATA"`, `RANGE = onboarded_at`, sparse INCLUDE projection — only items with
`onboarded_at`, i.e. `METADATA`, are present), so a `Select=COUNT` query over that index counts
leagues without a table scan.

## Goals / Non-Goals

**Goals:**
- Derive the count from truth (`METADATA` items) so it cannot drift.
- Delete the maintained-counter machinery (processor +1, API −1, orphan-script −1, the item).
- No infra/Terraform, no worker config changes.

**Non-Goals:**
- Changing the `/counts` endpoint contract or `get-counts` behavior.
- Changing the hourly cadence or introducing on-demand counting.
- Backfilling/deleting the retired `LEAGUE_COUNT` item as part of this change (harmless once unread).

## Decisions

- **Count via GSI3 `Select=COUNT`, paginated.** A single `QueryCommand` on `IndexName=GSI3`,
  `KeyConditionExpression="SK = :sk"`, `:sk = {S:"METADATA"}`, `Select="COUNT"`. DynamoDB returns
  `Count`/`ScannedCount` per page and paginates at the 1 MB scanned-per-page limit even for COUNT
  queries, so loop on `ExclusiveStartKey`/`LastEvaluatedKey`, summing `res.Count`. Alternative
  considered: a table `Scan` with a filter — rejected (full-table read, far costlier than the
  sparse index). `Select=COUNT` avoids transferring item bodies.
- **Home in `sync-counts`, not `get-counts`.** Keeps AWS credentials and the DynamoDB read off the
  public request path; reuses the existing cron and KV write. `get-counts` stays a pure KV reader.
- **Full removal of the counter, not deprecation.** Once the count is derived, nothing reads the
  `LEAGUE_COUNT` item, so the processor/API/script writes become dead writes; removing them is
  simpler than leaving drift-prone no-ops.
- **Wrap the query + KV write in try/catch; preserve the last good count on failure.** The GSI3
  query, the `COUNTS_KV.put`, and the success log live inside a `try`; the `catch` logs the reason
  (stack included, so an `AccessDeniedException` names the action/resource) via `console.error`.
  Because the `put` is inside the `try`, a failed run leaves the previously-synced KV value in
  place rather than clobbering a good count — the landing page keeps showing the last value instead
  of dropping to 0. The handler resolves normally (no re-throw), matching the existing
  credential-guard `return`, so a transient DynamoDB error is not retried as an unhandled
  invocation. Trade-off: a failed sync is recorded as a successful invocation in Cloudflare
  observability rather than an errored one; the `console.error` line is the signal to watch.
  Surfaced concretely while verifying the change — the old `GetItem` policy lacked `dynamodb:Query`
  on the `index/GSI3` ARN, and without this catch the failure was an opaque unhandled rejection.

## Risks / Trade-offs

- **Staleness up to one hour** → Unchanged from today (the sync was already hourly); acceptable for
  a social-proof number.
- **COUNT query cost grows with league count** → GSI3 is a sparse INCLUDE index with small
  projected items; a COUNT query over a few thousand leagues is a handful of RCUs per hour. Revisit
  only at a much larger scale.
- **Semantic drift from the old counter** → The old counter counted first-time onboards minus
  deletes; the derived count counts distinct `METADATA` items. These agree (one `METADATA` per
  canonical league; refresh/migrate reuse it; delete removes it), and the derived value is the more
  correct of the two.

## Migration Plan

1. Deploy the `sync-counts` worker change (GetItem → paginated GSI3 Query). On the next hourly tick
   KV is repopulated from the derived count. `get-counts`/`/counts` are untouched.
2. Deploy the backend change removing the increment/decrement writes.
3. Rollback: revert the worker to the `GetItem` version; the `LEAGUE_COUNT` item still exists (not
   deleted by this change), so the old read path works if the backend revert is also applied.
