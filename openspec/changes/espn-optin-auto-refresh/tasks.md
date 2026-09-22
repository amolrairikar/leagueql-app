## 1. ESPN credential storage (backend/espn-credential-storage)

- [x] 1.1 Add `src/common/espn_credentials.py` with `EspnCredentialClient` (mirror `YahooTokenClient`): `encrypt`/`decrypt` via KMS, `store_credentials(clerk_user_id, swid, espn_s2)` writing `USER#{id}/ESPN_CREDENTIALS`, `get_credentials(clerk_user_id)` → `(swid, espn_s2)` or raise `ESPNReauthRequired`, `delete_credentials(clerk_user_id)`, and `from_env()` reading `ESPN_KMS_KEY_ID`/`ESPN_KMS_REGION`/`DYNAMODB_TABLE_NAME`. Verify with new unit tests in `tests/unit/common/` (encrypt→decrypt round-trip, store/get/delete, missing item raises `ESPNReauthRequired`).
- [x] 1.2 Confirm no code path logs/returns plaintext cookies; verify by grepping and by a unit test asserting the stored attributes are ciphertext, not the input.

## 2. Onboarder: opt-in flag + ESPN credential handling (backend/league-onboarding)

- [x] 2.1 Thread an `autoRefresh` boolean from the invoke body through `src/onboarder/handler.py` → `OnboardingService`. Verify with a unit test that the flag reaches the service.
- [x] 2.2 In `src/onboarder/writer.py`, persist `auto_refresh_enabled` on the `METADATA` item (new-league and new-season-refresh paths), preserved across a new-season refresh. Verify with writer unit tests for both true/false and season-renewal preservation.
- [x] 2.3 On a successful opted-in ESPN onboard/refresh, store the owner's cookies via `EspnCredentialClient.store_credentials`; do not store on failure. Verify with onboarding-service unit tests (stored on success, not stored on auth failure).
- [x] 2.4 For an ESPN refresh invoked with `owner_user_id` and no cookies, fetch+decrypt via `EspnCredentialClient.get_credentials`; map `ESPNReauthRequired` → `ESPN_AUTH` failure (non-paging). Verify with unit tests (stored cookies used; missing cookies record `ESPN_AUTH` and dispatch no fetch).

## 3. Scheduler: opt-in gating + ESPN inclusion (backend/scheduled-league-auto-refresh)

- [x] 3.1 In `src/league_refresh/utils.py`, add `ESPN` to `REFRESH_PLATFORMS` and update the module comment. Generalize `_get_league_owner` to also project `auto_refresh_enabled`; select Yahoo and ESPN leagues only when the flag is true and an owner exists, dispatching ESPN with `owner_user_id` and no cookies. Verify with unit tests: ESPN/Yahoo selected only when flagged; unflagged/owner-less skipped; Sleeper unchanged.
- [x] 3.2 Add a backend component test (`tests/component/`, moto) for the ESPN scheduled-refresh chain end-to-end using a stored encrypted credential, asserting the onboarder is invoked with the owner and refreshes without cookies in the invoke.

## 4. API: auto-refresh endpoint + payload + cleanup (backend)

- [x] 4.1 Add `autoRefresh: bool = False` to `OnboardingPayload` in `src/api/main.py` and pass it through the onboarder invoke in `src/api/routes.py`. Verify with an API unit/component test that the flag is forwarded.
- [x] 4.2 Add owner-only `PUT /leagues/{leagueId}/auto-refresh` `{enabled: bool}` in `src/api/routes.py` that sets/clears `auto_refresh_enabled` on `METADATA`; on a change leaving the owner with no opted-in ESPN league, call `EspnCredentialClient.delete_credentials`. Verify with unit/component tests (enable/disable 200, non-owner 403, last-ESPN opt-out deletes credentials).
- [x] 4.3 Extend the delete-league path (`src/api/routes.py`) to delete `ESPN_CREDENTIALS` when the owner's last opted-in ESPN league is removed, best-effort (failures logged, never fail the delete). Verify with component tests mirroring the existing Yahoo cleanup scenarios.
- [x] 4.4 Update `docs/api/openapi_spec.yaml` (new endpoint + `autoRefresh` field) and `docs/db/dynamodb_spec.md` (new `ESPN_CREDENTIALS` item + `auto_refresh_enabled` attribute). Verify by review against the specs.

## 5. Infrastructure (shared KMS key)

- [x] 5.1 In `infrastructure/regional/main.tf`, add `ESPN_KMS_KEY_ID`/`ESPN_KMS_REGION` env vars to the API + onboarder Lambdas pointing at the existing shared key/region (`alias/leagueql-yahoo-token-${env}`, `us-east-1`). Verify with `terraform validate`/plan showing only the env-var additions and no new key/grant.
- [x] 5.2 Architecture diagram: no change needed — the ESPN credential store reuses the existing KMS key + DynamoDB table (no new deployed component / node).

## 6. Frontend: ESPN checkbox + API (frontend/connect-league)

- [x] 6.1 Add `autoRefresh: z.boolean()` (default false) to the `espn` variant in `features/connect_league/league-connect-schema.ts`. Verify types compile (`npm run build:ci`).
- [x] 6.2 Add the "enable automatic weekly refresh" checkbox + `HelpCircle`/`Tooltip` explainer to the ESPN block in `features/connect_league/league-connect.tsx`, prefilled from the league's `auto_refresh_enabled` on refresh. Include `autoRefresh` in the submit body and add `setAutoRefresh(leagueId, enabled)` to `features/connect_league/api-calls.ts`. Verify with jest-cucumber scenarios (checkbox on/off sends the flag; refresh prefills current enrollment).

## 7. Frontend: Yahoo opt-in + sidebar toggle (frontend/connect-yahoo-league, navigation-sidebar)

- [x] 7.1 Add the opt-in checkbox + tooltip to `features/connect_league/yahoo-connect-return.tsx` at link time, recording the choice. Verify with a jest-cucumber scenario.
- [x] 7.2 (Dropped per user request — no sidebar auto-refresh toggle.) Opt-in/out is managed through the connect/refresh-form checkbox (ESPN) and the Yahoo link flow; the backend `PUT /leagues/{id}/auto-refresh` endpoint and its `setAutoRefresh` client wrapper remain available. `features/sidebar/app-sidebar.tsx` carries no auto-refresh toggle.
- [x] 7.3 Update `features/sidebar/refresh-reminder-banner.tsx` copy/comment (non-behavioral) so it no longer frames ESPN as manual-only. Verify existing banner tests still pass.

## 8. Frontend: docs, privacy, changelog (frontend/instructions-docs, privacy-pages, changelog)

- [x] 8.1 Reword `features/privacy/privacy-page.tsx` and `features/privacy/extension-privacy-page.tsx`: ESPN cookies stored encrypted only when auto-refresh is enabled, used only to refresh league data, never shared, removed when turned off / last ESPN league removed; drop the "ESPN cookies are never stored" contrast. Verify against `frontend/privacy-pages` spec by review and any page tests.
- [x] 8.2 Update `features/instructions/instructions-page.tsx` "Refreshing League Data": add ESPN + Yahoo opt-in auto-refresh sub-subsections. Verify against `frontend/instructions-docs` spec.
- [x] 8.3 Add a changelog entry in `features/changelog/constants.ts` (template: the v1.7.0 Yahoo entry).

## 9. Validation

- [x] 9.1 Backend: `pipenv run ruff check --fix . && pipenv run ruff format .`; run `tests/unit` and `pipenv run behave tests/component`. Verify all pass with coverage close to 100% incl. error paths.
- [x] 9.2 Frontend (`frontend/`): `npm run format:fix && npm run lint`; `npx vitest run` for the touched features. Verify green.
- [x] 9.3 `openspec validate espn-optin-auto-refresh --strict` passes; then archive with `/opsx:archive` after implementation is complete.
