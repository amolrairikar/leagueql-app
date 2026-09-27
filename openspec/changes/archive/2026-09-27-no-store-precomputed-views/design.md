## Context

See proposal.md — Why. Relevant current state:

- Two GET endpoints send `Cache-Control: private, max-age=300`: `query_league`
  (`src/api/routes.py:882`) and `export_league` (`src/api/routes.py:967`). Every other route is
  `no-store` (explicit or via the `_security_headers` middleware `setdefault`, `src/api/main.py`).
- There is **no** CDN / CloudFront / API Gateway response cache in front of the API (it is an
  HTTP API v2, which has no response caching). The `max-age=300` is honored only by the
  **browser HTTP cache**.
- The frontend has an in-memory JS cache (`_cache` Map, `frontend/src/lib/api-client.ts`), TTL
  5 min for query reads, plus `_inflight` dedup. `clearApiCache()` is called after every
  mutation (delete/onboard/refresh) but can only clear the JS Map — never the browser HTTP cache.
- The `max-age=300` was a deliberate "Cache-Control audit" decision (documented in the
  `_security_headers` docstring and the `security-headers` spec).

## Goals / Non-Goals

**Goals:**
- Guarantee league data is never served stale from the browser after delete / re-onboard /
  manual refresh / scheduled auto-refresh.
- Collapse to a single, controllable cache layer (the JS cache) with no correctness gap.

**Non-Goals:**
- Changing the frontend JS cache, its TTL, or `clearApiCache()`.
- Adding ETag/conditional-request support or a CDN cache.
- Touching `get_league` / `get_job` (already `no-store`).

## Decisions

**Decision: set `no-store` on `/query` and `/export` (rather than a version-token cache key).**
The browser HTTP cache is the only layer serving stale data, and `no-store` removes it
completely and unconditionally. Rationale over the alternative (keep `max-age=300` but append a
`v=<last_refresh_at>` cache-busting param): the version-token approach requires plumbing a
freshness token into every `queryLeague` call and would still miss server-side
`scheduled-league-auto-refresh` (which never runs `getLeague`), leaving a staleness edge case.
`no-store` is simpler, has no edge cases, and leaves the in-session JS cache to provide perf.

**Decision: keep the `setdefault` default-deny middleware unchanged.** The mechanism still
matters (a future route can opt into a different policy, and routes that explicitly set
`no-store` must not be double-stamped). Only the illustrative spec scenario and the docstring
example change, because `/query` no longer opts into a cacheable value. The
`security-headers` "Route-set cache value preserved" scenario is re-pointed at `GET
/feature-flags`, which explicitly sets its own `no-store`.

## Risks / Trade-offs

- **Slightly more backend reads on hard reload / new tab within a 5-min window** → Mitigated by
  the untouched JS `_cache`/`_inflight`, which still serve all in-session SPA navigation. Each
  uncached `/query` is ~2–4 small DynamoDB reads (`lookup_league` + `get_league_metadata` +
  `read_view`; membership check reuses the fetched metadata) and no writes — cents/month at
  on-demand pricing; DynamoDB is on-demand so there is no throttling risk.
- **Spec/test coupling to the old example** → The `setdefault` unit test and the
  `security-headers` scenario both cited `/query`'s `private, max-age=300`; both are re-pointed
  at `/feature-flags` so the mechanism stays honestly covered.

## Migration Plan

Single deploy of the backend API (header change only). No data migration, no infra change, no
frontend deploy required. Rollback is a trivial revert of the two header lines. No client or
contract compatibility concern — `no-store` is a strictly safe direction (clients simply stop
caching).
