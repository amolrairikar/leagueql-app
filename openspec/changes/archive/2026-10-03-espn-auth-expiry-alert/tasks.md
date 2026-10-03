# Tasks

## 1. Credential flag

- [x] 1.1 Add `get_stored_credentials` and `mark_auth_failed` to `src/common/espn_credentials.py`; verify with `tests/unit/common/test_espn_credentials.py`

## 2. Onboarder

- [x] 2.1 Record `error_status` in `fetch_one` and raise `UpstreamAuthError` from `validate_api_results` when every failure is `401`/`403`; verify with onboarder `test_utils.py`
- [x] 2.2 In `src/onboarder/handler.py`, map `UpstreamAuthError` to `ESPN_AUTH` (ESPN) and mark stored credentials on any stored-cookie `ESPN_AUTH`; verify with onboarder `test_handler.py`

## 3. Scheduled refresh

- [x] 3.1 Skip ESPN leagues whose owner's credentials carry `auth_failed_at` in `src/league_refresh/utils.py`; verify with league_refresh unit tests

## 4. API

- [x] 4.1 Return `espn_reauth_required` / `espn_credentials_failed_at` from `GET /leagues/{leagueId}`; verify with API unit tests
- [x] 4.2 Update `docs/api/openapi_spec.yaml` and `docs/db/dynamodb_spec.md`

## 5. Frontend

- [x] 5.1 Add the fields to `GetLeagueResponse` and expose `espnReauthRequired` from `useIsOwner`
- [x] 5.2 Add `EspnReauthBanner` and render it below the header; add jest-cucumber feature + steps
- [x] 5.3 Show "Update ESPN Cookies" in the sidebar and pre-check auto-refresh in the dialog; extend sidebar tests

## 6. Component coverage

- [x] 6.1 Behave: scheduled ESPN refresh rejected → credentials flagged → next run skips; GET league reports `espn_reauth_required` to the owner only and clears after re-store

## 7. Checks

- [x] 7.1 Ruff, pytest, behave, vitest, lint, format, `build:ci`, and `openspec validate espn-auth-expiry-alert --strict` all pass
