## 1. Backend — expose refresh/onboard timestamps

- [x] 1.1 In `src/api/routes.py` `get_league`, add `last_refresh_at` (from `metadata.get("last_refresh_at")`) and `onboarded_at` (from `metadata.get("onboarded_at")`) to the response `data` dict; verify by inspecting the returned payload in the unit test below.
- [x] 1.2 In `docs/api/openapi_spec.yaml`, add `last_refresh_at` (string, ISO 8601, nullable) and `onboarded_at` (string, ISO 8601) to the `LeagueFoundData` schema and update the `LeagueFoundResponse` example; keep `required: [seasons]`. Verify with `openspec validate` and a YAML lint/parse.
- [x] 1.3 Extend `tests/unit/api/test_endpoints.py` `get_league` tests: one case asserting `last_refresh_at` present, one onboard-only case asserting `last_refresh_at` is `None` while `onboarded_at` is set. Verify `pipenv run pytest tests/unit/api/test_endpoints.py` passes.
- [x] 1.4 If any `tests/component` scenario asserts the `GET /leagues/{id}` body shape, update it and its steps to include the new fields. Verify `pipenv run behave tests/component` passes.

## 2. Frontend — data plumbing

- [x] 2.1 In `frontend/src/components/api/types.ts`, add `last_refresh_at?: string | null;` and `onboarded_at?: string;` to `GetLeagueResponse.data`. Verify with `npm run build:ci`.
- [x] 2.2 In `frontend/src/lib/demo-api.ts` `getDemoLeague`, return a recent `onboarded_at`/`last_refresh_at` (or omit) consistent with the new shape so the demo league is never stale. Verify demo tests still pass.
- [x] 2.3 Add `useLeagueFreshness()` beside `frontend/src/features/ownership/use-is-owner.ts`, returning `{ loading, lastUpdated: Date | null }` where `lastUpdated = last_refresh_at ?? onboarded_at` (parsed to `Date`), bypassing in demo/no-league like `useIsOwner`. Verify via the banner component test below.

## 3. Frontend — banner

- [x] 3.1 Create `frontend/src/features/sidebar/refresh-reminder-banner.tsx`: bail (`return null`) in demo mode, no league, or `platform !== 'ESPN'`; use `useIsOwner()` + `useLeagueFreshness()`; render nothing while loading, if not owner, if `lastUpdated` is null, or if `Date.now() - lastUpdated.getTime() <= 7*24*60*60*1000`; otherwise render the thin `h-8` bar (model on `components/banner.tsx`, no link, no dismiss button) with the message `Refresh your ESPN league data by clicking the "Refresh League" button in the sidebar!`. Verify via 3.3.
- [x] 3.2 Render `<RefreshReminderBanner />` in `AppLayout` (`frontend/src/app/app.tsx`) next to `<Banner />`. Verify the app builds and the banner appears on main-app routes in the e2e check.
- [x] 3.3 Add a jest-cucumber pair under `frontend/src/features/sidebar/__tests__/` (`refresh-reminder-banner.feature` + `.steps.test.tsx`) with MSW-mocked `getLeague` covering: ESPN+owner+stale (`last_refresh_at` >7d) → shown; ESPN+owner+fresh → hidden; ESPN+owner+onboard-only (>7d shown, <7d hidden); Sleeper → hidden; ESPN non-owner → hidden; demo mode → hidden. Verify `npx vitest run frontend/src/features/sidebar/__tests__/refresh-reminder-banner.steps.test.tsx` passes.

## 4. Quality gates

- [x] 4.1 Backend lint/format: `pipenv run ruff check --fix .` and `pipenv run ruff format .`.
- [x] 4.2 Frontend lint/format (from `frontend/`): `npm run format:fix` and `npm run lint`.
- [x] 4.3 Run full relevant suites: `pipenv run pytest tests/unit/api/test_endpoints.py`, `pipenv run behave tests/component`, and `npx vitest run` (frontend). Verify all green.
- [x] 4.4 `openspec validate --all` passes.
