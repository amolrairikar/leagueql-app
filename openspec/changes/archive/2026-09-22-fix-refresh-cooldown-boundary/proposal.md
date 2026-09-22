## Why

The manual refresh cooldown uses an exact-duration comparison (`elapsed < timedelta(days=7)`)
measured to the second from the stored `last_refresh_at`. A league refreshed at 10:00 cannot be
refreshed again until 10:00 seven days later, so a legitimate ~weekly refresh attempted earlier in
the day on the seventh day (e.g. 08:00, only 6d 22h elapsed) is wrongly rejected with a `429`. The
cooldown is meant to enforce "once per week", not "once per 7×24 hours".

## What Changes

- Measure the weekly refresh cooldown in whole UTC calendar days instead of an exact 7×24h
  duration. A refresh is permitted once the current UTC date is at least `REFRESH_COOLDOWN_DAYS`
  (7) days after the UTC date of the most recent successful refresh, regardless of the time of day
  either occurred. The `429` message and its remaining-wait phrasing (now computed to the next
  allowed UTC calendar day) and the DEV bypass are unchanged.

This affects only the manual `POST /leagues?requestType=REFRESH` path. The scheduled auto-refresher
(`src/league_refresh/`) does not consult `last_refresh_at` and is unaffected.

## Capabilities

### Modified Capabilities
- `backend/league-refresh`: the weekly cooldown is measured in whole UTC calendar days rather than
  an exact rolling 7×24h window, so a refresh 7 calendar days later at any time of day is allowed.

## Impact

- **Backend:** `src/api/routes.py` (cooldown comparison in the REFRESH branch).
- **API contract:** `docs/api/openapi_spec.yaml` `TooManyRequests` description wording (calendar-day
  semantics).
- **Tests:** backend unit (`tests/unit/api/test_endpoints.py`) — add a boundary case; existing
  within/outside/DEV cooldown tests still pass.
