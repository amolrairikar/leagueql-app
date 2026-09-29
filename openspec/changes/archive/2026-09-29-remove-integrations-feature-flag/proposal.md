# Proposal

## Why

The community Integrations page has launched. The `integrations` feature flag that hid the page, its
sidebar item, and the `/integrations` endpoints is now always on, so the gate is dead weight.

## What Changes

- **BREAKING (flag payload only)**: `GET /feature-flags` no longer returns an `integrations` key.
- `GET /integrations` and `POST /integrations` are always served (still auth-gated); they never 404
  on a flag.
- The sidebar always shows the "Community" group with the "Integrations" item, and `/integrations`
  always renders the Integrations page.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/integrations`: the feature-flag gate requirement is removed.
- `frontend/integrations`: the feature-flag gate is replaced by an always-on nav item and route.

## Impact

- **Backend**: `src/common/feature_flags.py` (drop `INTEGRATIONS`), `src/api/routes.py` (drop
  `require_integrations_enabled` and the payload key); unit + component tests.
- **Frontend**: `lib/feature-flags.ts` (drop `isIntegrationsEnabled`), `features/sidebar/app-sidebar.tsx`,
  `app/app.tsx` (route renders `IntegrationsPage` directly; `integrations-route.tsx` removed);
  component tests.
- **Docs**: `docs/api/openapi_spec.yaml` (drop the 404 responses and the `integrations` flag).
- **Ops**: the `integrations` key can be deleted from the SSM `/leagueql/<env>/feature-flags`
  parameter after deploy; it is ignored either way.
