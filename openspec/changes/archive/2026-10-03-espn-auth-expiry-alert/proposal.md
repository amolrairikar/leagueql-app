# Proposal

## Why

ESPN `espn_s2`/`SWID` cookies expire, and ESPN offers no way to renew them from code. When a
scheduled auto-refresh runs with an owner's stored cookies after they expire, ESPN answers `401`
(`AUTH_LEAGUE_NOT_VISIBLE`). Today that outcome is written only to a `JOB_STATUS` item keyed by a
correlation ID the owner never sees, and the item expires after 24 hours. The league silently stops
updating and the owner has no way to find out or fix it.

A `401` on the async per-week fetches is also misclassified as `UPSTREAM`, which pages Discord for
what is really an expected user-credential problem.

## What Changes

- When a scheduled ESPN refresh (stored cookies) is rejected for auth, the onboarder marks the
  owner's `ESPN_CREDENTIALS` item with `auth_failed_at`. The mark is conditional on the item's
  `updated_at`, so cookies the owner re-entered mid-run are never flagged.
- Re-storing cookies replaces the item, which clears the flag.
- An onboard/refresh whose every season failed and every failure was a `401`/`403` is classified
  `ESPN_AUTH` (ESPN) instead of `UPSTREAM`, so it no longer pages.
- The scheduled refresh skips ESPN leagues whose owner's stored cookies are flagged.
- `GET /leagues/{leagueId}` returns `espn_reauth_required` (and `espn_credentials_failed_at`) to the
  owner of an auto-refresh-enabled ESPN league whose stored cookies are flagged or missing.
- The frontend shows a non-dismissible banner to that owner and an "Update ESPN Cookies" sidebar
  action that opens the refresh dialog with auto-refresh pre-checked.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/espn-credential-storage`: rejection flag, conditional mark, cleared on re-store.
- `backend/league-onboarding`: all-auth-failure classification; stored-cookie rejection marks the
  credentials.
- `backend/scheduled-league-auto-refresh`: skip flagged owners.
- `backend/league-metadata`: `espn_reauth_required` / `espn_credentials_failed_at`.
- `frontend/refresh-reminder-banner`: ESPN re-auth banner.
- `frontend/navigation-sidebar`: "Update ESPN Cookies" action.

## Impact

- `src/common/espn_credentials.py`, `src/onboarder/{utils,handler}.py`,
  `src/league_refresh/utils.py`, `src/api/routes.py`.
- Frontend: `use-is-owner.ts`, `app-sidebar.tsx`, `refresh-league-dialog.tsx`, new
  `espn-reauth-banner.tsx`, API types.
- Docs: `docs/db/dynamodb_spec.md`, `docs/api/openapi_spec.yaml`.
