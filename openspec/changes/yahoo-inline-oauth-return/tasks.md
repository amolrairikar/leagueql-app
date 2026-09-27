# Tasks

## 1. Frontend: resume the Yahoo OAuth return inline on the landing page

- [x] 1.1 In `frontend/src/features/landing_page/landing-page.tsx`, refactor `handleYahooConnect` to accept an optional `autoRefresh` override (default to the `yahooAutoRefresh` checkbox state) so the return path can pass the persisted opt-in; verify the existing normal-submit Yahoo path still compiles and behaves the same (checkbox state used when no override).
- [x] 1.2 Add a mount effect keyed on `isSignedIn` and guarded by a `startedRef` that reads `platform`/`yahooLinked`/`leagueId` from the URL; on `platform=YAHOO` set Yahoo selected and open the connect form. On `yahooLinked=1` + a `leagueId`, `setLoading(true)` and resume via `handleYahooConnect(leagueId, takeYahooAutoRefreshPref())`; on `yahooLinked=0`, show the inline retry alert ("Yahoo linking was cancelled or failed — try again"). Then strip the params via `history.replaceState`. Verify by loading `/` with each param set (manually or via test) that the correct branch runs and a reload does not re-trigger.
- [x] 1.3 Add jest-cucumber scenarios in `frontend/src/features/landing_page/__tests__/landing-connect.feature` + `.steps.test.tsx` for: linked return onboards inline (progress → `/home`), already-onboarded (null `data`) routes in, `yahooLinked=0` inline retry alert, auto-refresh opt-in applied on return (assert the MSW-observed `POST /leagues` body), and revoked (`YAHOO_AUTH`) on resume restarts OAuth. Verify with `npx vitest run src/features/landing_page/__tests__/landing-connect.steps.test.tsx`.

## 2. Frontend: collapse `/connect_league` to a redirect shim

- [x] 2.1 In `frontend/src/features/connect_league/league-connect.tsx`, replace the `YahooConnectReturn` render with a redirect that forwards the Yahoo return params to `/` (`<Navigate to={/?<preserved params>} replace />`), keeping the existing non-Yahoo `→ /?connect=true` fallback. Delete `frontend/src/features/connect_league/yahoo-connect-return.tsx`. Verify `tsc`/build has no dangling imports and the `/connect_league` route still resolves.
- [x] 2.2 Move any still-relevant assertions out of `frontend/src/features/connect_league/__tests__/yahoo-connect.feature` + `.steps.test.tsx` into the landing tests (task 1.3), then delete that test pair (component removed). Verify with `npm run test` that the suite passes with no orphaned references to `YahooConnectReturn`.

## 3. Backend + infra: return the callback to the landing page

- [x] 3.1 In `src/api/main.py`, change the `YAHOO_CONNECT_RETURN_URL` default from `https://leagueql.app/connect_league` to `https://leagueql.app/`. Update `infrastructure/regional/vars.tf` `yahoo_connect_return_url` default to match (leave `main.tf` wiring and `YAHOO_MIGRATE_RETURN_URL`/`YAHOO_REDIRECT_URI` unchanged). Verify the callback in `src/api/routes.py` still appends `?platform=YAHOO&yahooLinked=…&leagueId=…` to the new base.
- [x] 3.2 Update backend tests that assert the ONBOARD-flow return URL to expect the landing root: check `tests/unit/api/` and `tests/component/` for `/connect_league` assertions on the callback and change the expected base to `/` (migrate-flow assertions unchanged). Verify with `pipenv run pytest tests/unit` and `pipenv run behave tests/component`.

## 4. Quality gates and end-to-end verification

- [x] 4.1 Lint/format: `cd frontend && npm run format:fix && npm run lint`; backend `pipenv run ruff check --fix . && pipenv run ruff format .`. Verify clean.
- [x] 4.2 Run `openspec validate --all` (green) and the full frontend (`npm run test`) + backend (`pipenv run pytest tests/unit && pipenv run behave tests/component`) suites; confirm ESPN/Sleeper inline onboarding and the `/migrate_league` Yahoo return are unaffected.
