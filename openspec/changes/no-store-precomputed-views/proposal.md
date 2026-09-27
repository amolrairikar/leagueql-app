## Why

After a user deletes and re-onboards, or manually refreshes, a league, the app can display
**stale data for up to 5 minutes**. The two league-data GET endpoints send
`Cache-Control: private, max-age=300`, so the browser's own HTTP cache keeps re-serving the
pre-mutation response at the unchanged URL. The frontend's `clearApiCache()` only clears its
in-memory JS cache; it cannot evict the browser HTTP cache. (The same layer also masks
server-side scheduled auto-refresh updates.)

## What Changes

- `GET /leagues/{leagueId}/query` and `GET /leagues/{leagueId}/export` change from
  `Cache-Control: private, max-age=300` to `Cache-Control: no-store`, so the browser never
  independently caches league data. The frontend in-memory JS cache (already cleared by
  `clearApiCache()` on every mutation) becomes the single cache layer.
- No production route opts into a browser-cacheable `Cache-Control` value anymore. The
  middleware `setdefault` default-deny mechanism is unchanged (a future route can still
  override), but the spec scenario that illustrated it with `/query` is re-pointed at a route
  that sets its own `no-store`.
- The OpenAPI contract's documented `Cache-Control` examples for these two responses are
  updated to `no-store`.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/query-precomputed-views`: the query response cache header changes from
  `private, max-age=300` to `no-store`.
- `backend/league-export`: the export response cache header changes from
  `private, max-age=300` to `no-store`.
- `backend/security-headers`: the "Route-set cache value preserved" scenario no longer uses
  `/query`'s `private, max-age=300` opt-in (no route sets a cacheable value now); it is
  reframed around a route that sets its own `Cache-Control` still being preserved by
  `setdefault`. The default-deny requirement itself is unchanged.

## Impact

- **Backend code:** `src/api/routes.py` (`query_league`, `export_league` headers),
  `src/api/main.py` (`_security_headers` docstring reference to the `/query` opt-in).
- **API contract:** `docs/api/openapi_spec.yaml` (`QuerySuccessResponse`,
  `ExportSuccessResponse` `Cache-Control` header examples/descriptions).
- **Tests:** backend unit (`tests/unit/api/test_endpoints.py`) and backend component
  (`tests/component/features/api_query.feature`, `api_export.feature`).
- **Frontend:** no change — the JS `_cache`/`clearApiCache()` behavior is unchanged and remains
  the perf cache for in-session navigation.
- **Behavior:** guaranteed-fresh league data after delete/re-onboard/refresh/auto-refresh; a
  slightly slower first paint on a hard reload or new tab within a 5-minute window. Negligible
  extra DynamoDB/Lambda cost (a few small reads per uncached query, no writes).
- **No infra change:** no CDN/API Gateway caches these responses; Terraform is untouched.
