## 1. Backend headers

- [x] 1.1 In `src/api/routes.py`, change `query_league`'s response header (currently line ~882) from `private, max-age=300` to `no-store`; verify by reading the code and by the unit test in task 3.2.
- [x] 1.2 In `src/api/routes.py`, change `export_league`'s response header (currently line ~967) from `private, max-age=300` to `no-store`; verify via the unit test in task 3.3.
- [x] 1.3 In `src/api/main.py`, update the `_security_headers` docstring so it no longer cites `GET /leagues/{id}/query` keeping `private, max-age=300`; state that every response now falls back to `no-store` and `setdefault` still lets a future route override. Verify the docstring reads correctly.

## 2. API contract

- [x] 2.1 In `docs/api/openapi_spec.yaml`, update `QuerySuccessResponse` and `ExportSuccessResponse` `Cache-Control` header `example` to `no-store` and fix the `description` (no longer "cache privately for 5 minutes"). Verify by grep that no `max-age=300` remains for these responses.

## 3. Backend unit tests

- [x] 3.1 In `tests/unit/api/test_endpoints.py`, re-point `test_default_does_not_override_route_cache_control` (~:50) at a route that explicitly sets its own `Cache-Control` (e.g. `GET /feature-flags`, which sets `no-store`), asserting the route's value is preserved; update the comment. Verify the test passes.
- [x] 3.2 Update the query `test_cache_control_header_set` (~:1116) to assert `no-store`. Verify it passes.
- [x] 3.3 Update the export `test_cache_control_header_set` (~:2306) to assert `no-store`. Verify it passes.
- [x] 3.4 Run `pipenv run pytest tests/unit/api/test_endpoints.py` and the full `pipenv run pytest tests/unit/`; verify all pass with coverage near 100%.

## 4. Backend component tests

- [x] 4.1 In `tests/component/features/api_query.feature`, change the Cache-Control step to `no-store`. Verify via task 4.3.
- [x] 4.2 In `tests/component/features/api_export.feature`, change the Cache-Control step to `no-store`. Verify via task 4.3.
- [x] 4.3 Run `pipenv run behave tests/component`; verify the api_query and api_export scenarios pass.

## 5. Lint, validate, and end-to-end verification

- [x] 5.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`; verify no lint/format errors.
- [x] 5.2 Run `openspec validate no-store-precomputed-views --strict`; verify the change is valid.
- [x] 5.3 Manually verify end-to-end: open a league, note a `/query` view (e.g. standings), then manually refresh (or delete + re-onboard); confirm the view updates immediately and DevTools shows `/query` responding with `Cache-Control: no-store` and re-fetching (200, not "from disk cache") after the mutation and on hard reload.
