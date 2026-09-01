## Why

Each manual league refresh re-runs the full onboarder → processor pipeline, which is
expensive and rarely produces new data more than once a week (fantasy weeks settle weekly).
The existing per-league cooldown is only 30 minutes, and the frontend silently discards the
cooldown response, showing a misleading generic "please try again." We want to cap manual
refreshes at once per week and tell the user clearly when they can refresh again.

## What Changes

- Widen the per-league manual refresh cooldown from 30 minutes (`REFRESH_COOLDOWN_MINUTES = 30`)
  to a rolling 7-day window (`REFRESH_COOLDOWN_DAYS = 7`) in the `POST /leagues?requestType=REFRESH`
  cooldown check.
- Replace the minutes-based `429` `detail` with a human-readable remaining-wait message
  (e.g. "This league can only be refreshed once per week. You can refresh again in 5 days."),
  produced by a small testable helper.
- Frontend: stop discarding the non-retryable `429` cooldown (and `409` already-up-to-date /
  in-progress) response. Surface the backend `detail` as a **benign** notice — neutral title, no
  contact-support prompt — reusing the existing `NOT_STARTED` special-case pattern instead of the
  red "Refresh Failed" alert.
- The scheduled Sleeper auto-refresh path is unchanged; it writes `last_refresh_at` and therefore
  now gates a manual Sleeper refresh for up to 7 days. This is acceptable because the existing
  "already up to date" `409` short-circuit already covers the common case. No exemption logic is
  added.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `backend/league-refresh`: requirement "Enforce refresh cooldown and concurrency" — the cooldown
  window becomes a weekly (7-day) window and the `429` carries a human-readable remaining-wait
  message.
- `frontend/connect-league`: requirement "Surface errors inline and refresh cache on success" — a
  `429` cooldown (and `409` already-up-to-date / in-progress) response is surfaced to the user as a
  benign notice using the backend `detail`, not a generic failure.

## Impact

- Backend: `src/api/main.py` (constant), `src/api/routes.py` (cooldown check + message helper).
- Frontend: `frontend/src/features/connect_league/league-connect.tsx` (capture and surface the
  benign response).
- Tests: `tests/unit/api/test_endpoints.py`, `tests/component/features/league_refresh.feature`
  (+ steps), `frontend/src/features/connect_league/__tests__/connect-league.{feature,steps.test.tsx}`.
- Docs: `docs/db/dynamodb_spec.md` (`last_refresh_at` wording), `docs/api/openapi_spec.yaml`
  (document the `429` on `/leagues`).
- No DynamoDB schema change (reuses existing `last_refresh_at`), no infrastructure change.
