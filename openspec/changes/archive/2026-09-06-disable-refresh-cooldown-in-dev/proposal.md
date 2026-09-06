## Why

The refresh endpoint enforces a rolling 7-day per-league cooldown, returning `429` for a
second refresh within a week of the last successful one. In DEV this makes iterating on the
refresh pipeline painful — you must wait a week or hand-edit `last_refresh_at` in DynamoDB
between test refreshes. We want the cooldown to be a no-op in DEV while leaving PROD unchanged.

## What Changes

- Skip the 7-day cooldown check when the API runs with `ENVIRONMENT == "dev"`, so DEV refreshes
  are never blocked by `429`.
- No change to PROD: the cooldown still fires there. No change to the other refresh guards
  ("refresh already in progress" `409`, "already up to date / NFL offseason" `409`) in any
  environment.

## Capabilities

### Modified Capabilities
- `backend/league-refresh`: The "Enforce refresh cooldown and concurrency" requirement is
  relaxed so the weekly cooldown does not apply in the DEV environment (PROD behavior
  unchanged; concurrency and up-to-date guards still apply everywhere).

## Impact

- Backend: `src/api/routes.py` — guard the cooldown block with `os.environ.get("ENVIRONMENT")`
  (already injected into the API Lambda). No infra, frontend, or DynamoDB change.
- Tests: backend unit (`tests/unit/api/test_endpoints.py`) and, if applicable, component
  (`tests/component/features/league_refresh.feature`).
