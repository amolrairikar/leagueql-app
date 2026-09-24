# Proposal

## Why

Today a single failed API call during onboarding aborts the **entire** onboard: a
user onboarding an ESPN league across 2022–2026 who lacks access to the 2022/2023
season data (ESPN returns `401 AUTH_LEAGUE_NOT_VISIBLE`) gets nothing, even though the
2024–2026 fetches all succeeded. We should onboard the seasons that fully succeeded and
skip only the ones that failed.

## What Changes

- The onboarder becomes **season-resilient**: it onboards every season whose API calls
  all succeed and silently skips any season for which at least one API call failed.
- The onboard fails as a whole (unchanged `UPSTREAM`/502 behavior) **only when every
  season failed**.
- Skipped seasons produce no S3 payload, no processed views, and no entry in the
  league's recorded season set — exactly as if they had not been requested.
- Applies to all platforms (ESPN, Sleeper, Yahoo), since the failure check lives in the
  shared fetch-validation path.
- The change is silent to the user: only the accessible seasons appear in the UI; there
  is no new "some seasons were skipped" surface. No API-contract or DynamoDB schema
  change.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `backend/league-onboarding`: relax the all-or-nothing fetch-validation requirement to
  per-season resilience — skip a season whose fetch failed rather than failing the whole
  onboard, failing overall only when all seasons fail. Reconcile the Sleeper
  "genuine bracket fetch failure" scenario and the job-status "partial data" failure
  wording with the new behavior.

## Impact

- Code: `src/onboarder/utils.py` (`validate_api_results`),
  `src/onboarder/sleeper_client.py` (`fetch_all` — validate once over combined
  results), `src/onboarder/onboarding_service.py` (`run` — record only onboarded
  seasons). ESPN and Yahoo clients inherit the new behavior through the shared validator
  with no structural change.
- Tests: backend unit (`tests/unit/onboarder/`) and backend component
  (`tests/component/`, new multi-season fixture + scenarios).
- No changes to `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md`, the
  architecture diagram, or the frontend.
