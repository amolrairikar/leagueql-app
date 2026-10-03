# Tasks

## 1. Backend

- [x] 1.1 Move the refresh block checks into `_refresh_block_reason` (returns the 409/429 or `None`); verify existing refresh unit tests still pass
- [x] 1.2 Add `_fetch_espn_league_teams` and use it in `get_espn_members`; verify members proxy tests still pass
- [x] 1.3 Add `_enroll_blocked_espn_auto_refresh` (validate → store → flag; 400/502/500 paths) and call it for opted-in ESPN requests with cookies before raising the block; verify with `TestBlockedRefreshEnrollsAutoRefresh` across all four block types and every error path
- [x] 1.4 Add `store_credentials` to `src/api/espn_credentials.py`; verify with `tests/unit/api/test_espn_credentials.py`
- [x] 1.5 Component scenarios in `league_refresh.feature`: opted-in cooldown block enrolls and stores decryptable cookies; rejected cookies → 400 with nothing stored

## 2. Frontend

- [x] 2.1 Refresh dialog: opted-in 409/429 → "Automatic refresh enabled" notice, cookies cleared, Done button, reload on close; 400 → backend message; verify with the new `refresh-league.feature` scenarios

## 3. Docs

- [x] 3.1 Document the blocked-refresh enrollment and the 400/502 responses on `POST /leagues` in `docs/api/openapi_spec.yaml`
