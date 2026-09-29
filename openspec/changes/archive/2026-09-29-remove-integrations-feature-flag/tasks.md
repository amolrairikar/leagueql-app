# Tasks

## 1. Backend

- [x] 1.1 Remove `INTEGRATIONS` from `src/common/feature_flags.py`.
- [x] 1.2 Remove `require_integrations_enabled` and the `integrations` key from `GET /feature-flags` in `src/api/routes.py`.
- [x] 1.3 Update unit tests (`tests/unit/api/test_endpoints.py`, `test_integration_endpoints.py`) and the component feature (`tests/component/features/integrations.feature` + steps).

## 2. Frontend

- [x] 2.1 Remove `isIntegrationsEnabled` from `lib/feature-flags.ts` and its unit test.
- [x] 2.2 Always render the Community group in `app-sidebar.tsx`.
- [x] 2.3 Route `/integrations` to `IntegrationsPage` directly and delete `integrations-route.tsx`.
- [x] 2.4 Replace the flag-gating component tests with an always-on nav/route test.

## 3. Docs & quality

- [x] 3.1 Update `docs/api/openapi_spec.yaml`.
- [x] 3.2 Run ruff, `npm run format:fix`, `npm run lint`, `npm run build:ci`, pytest, behave, vitest, and `openspec validate --all`.
