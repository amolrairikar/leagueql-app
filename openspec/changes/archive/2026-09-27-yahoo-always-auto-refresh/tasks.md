# Tasks

## 1. Backend: always select Yahoo leagues in the scheduled refresh

- [x] 1.1 In `src/league_refresh/utils.py`, split the combined Yahoo/ESPN branch of `get_leagues_to_refresh` so Yahoo is skipped only when `owner_user_id` is missing and ESPN still requires `auto_refresh_enabled`; update the module comment and docstrings to match. Verify with `pipenv run pytest tests/unit/league_refresh`.
- [x] 1.2 Update `tests/unit/league_refresh/test_utils.py`: replace `test_skips_yahoo_league_not_opted_in` with a test that a Yahoo league with an owner and `auto_refresh_enabled` false/absent IS selected, keep the no-owner / missing-METADATA skip tests, and keep an ESPN not-opted-in skip test. Verify the file passes and `utils.py` coverage stays at 100%.
- [x] 1.3 Update `tests/component/features/league_auto_refresh.feature` (+ `tests/component/steps/league_refresh_steps.py` if needed): the "not opted into auto-refresh is skipped" scenario becomes "a Yahoo league not opted in is still refreshed with its owner", add/keep an ESPN not-opted-in skip scenario, and fix the feature description. Verify with `pipenv run behave tests/component/features/league_auto_refresh.feature`.
- [x] 1.4 Update `docs/db/dynamodb_spec.md` and `docs/api/openapi_spec.yaml` descriptions of `auto_refresh_enabled` to say it gates scheduled refresh for ESPN only (Yahoo is always refreshed). Verify by grepping both files for `auto_refresh_enabled` and checking each mention.
- [x] 1.5 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`; verify both are clean.

## 2. Frontend: remove the Yahoo opt-in from the connect flow

- [x] 2.1 In `frontend/src/features/landing_page/landing-page.tsx`, remove the `yahooAutoRefresh` state, the Yahoo checkbox + tooltip, the `autoRefreshOverride` parameter of `handleYahooConnect`, and all `setYahooAutoRefreshPref` / `takeYahooAutoRefreshPref` calls, rendering nothing in its place. Verify the page builds (`npm run build:ci`).
- [x] 2.2 Update `onboardYahooLeague` in `frontend/src/features/connect_league/api-calls.ts` to take no opt-in and omit `autoRefresh` from the Yahoo `POST /leagues` body; delete `frontend/src/features/connect_league/yahoo-auto-refresh-pref.ts`. Verify with `grep -rn "YahooAutoRefreshPref\|yahoo-auto-refresh" frontend/src` returning nothing.
- [x] 2.3 Update `frontend/src/features/landing_page/__tests__/landing-connect.feature` + `landing-connect.steps.test.tsx`: replace the two Yahoo auto-refresh scenarios with (a) selecting Yahoo shows no auto-refresh checkbox or note, (b) an in-place Yahoo connect sends no `autoRefresh`, and (c) the OAuth-return resume sends no `autoRefresh`. Verify with `npx vitest run src/features/landing_page`.
- [x] 2.4 Rewrite the Yahoo "Refreshing League Data" sub-subsection in `frontend/src/features/instructions/instructions-page.tsx` to say Yahoo leagues refresh automatically each week during the season using the connected Yahoo account, with nothing to enable and no manual refresh action; update any `/docs` copy assertion in `static-pages.feature` / steps that covers it. Verify with `npx vitest run src/features/landing_page/__tests__/static-pages`.
- [x] 2.5 Run `npm run format:fix` and `npm run lint` from `frontend/`; verify both are clean.

## 3. Integration checks

- [x] 3.1 Run the full suites — `pipenv run pytest tests/unit`, `pipenv run behave tests/component`, and `npm run test` + `npm run build:ci` in `frontend/` — and verify all pass.
- [x] 3.2 Run `npx @fission-ai/openspec@latest validate --all` and verify the change and specs are valid.
