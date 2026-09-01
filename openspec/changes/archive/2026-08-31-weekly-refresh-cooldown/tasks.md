## 1. Backend — widen cooldown to weekly

- [x] 1.1 In `src/api/main.py`, replace `REFRESH_COOLDOWN_MINUTES = 30` with `REFRESH_COOLDOWN_DAYS = 7`; verify no other reference to the old name remains (`grep -rn REFRESH_COOLDOWN_MINUTES src/`)
- [x] 1.2 Add a module-level helper `_format_cooldown_wait(remaining: timedelta) -> str` (in `src/api/routes.py`) that renders the remaining wait as days (and sub-day hours); verify via new unit test in 3.3
- [x] 1.3 In `src/api/routes.py` cooldown block, change the window to `timedelta(days=REFRESH_COOLDOWN_DAYS)`, update the import, and replace the `429` `detail` with a once-per-week message using the helper (e.g. "This league can only be refreshed once per week. You can refresh again in <wait>."); verify the endpoint still returns `429` within the window and `201` outside it (tasks 3.1–3.2)

## 2. Frontend — surface the benign cooldown/up-to-date message

- [x] 2.1 In `frontend/src/features/connect_league/league-connect.tsx`, capture the caught `ApiError` in the submit retry loop and, in the `!onboardSucceeded` branch, when status is `429` or `409` set `failureReason` to `err.message` and a `COOLDOWN` sentinel `failureCode` instead of nulling it
- [x] 2.2 In the failed-state alert, render the `COOLDOWN` code as a benign notice — neutral title (not "Refresh Failed") and no contact-support prompt — reusing the `NOT_STARTED` special-case pattern; verify via the frontend scenario in 3.4

## 3. Tests

- [x] 3.1 Update `tests/unit/api/test_endpoints.py::test_refresh_returns_429_when_within_cooldown` — 5-minute offset stays within the week; update any asserted message text; verify it still asserts `429`
- [x] 3.2 Update `test_refresh_proceeds_when_outside_cooldown` — change the 2-hour offset to `timedelta(days=8)` so it still asserts `201`
- [x] 3.3 Add a unit test for `_format_cooldown_wait` covering the multi-day and sub-day/hours branches; verify `pipenv run pytest tests/unit/api/` passes
- [x] 3.4 Add a backend component scenario in `tests/component/features/league_refresh.feature` (+ steps): `last_refresh_at` within the past week → `REFRESH` returns `429` with the once-per-week message; verify `pipenv run behave tests/component` passes
- [x] 3.5 Add a frontend scenario in `frontend/src/features/connect_league/__tests__/connect-league.{feature,steps.test.tsx}`: MSW mocks `POST /leagues` → `429` with the cooldown `detail`; assert the exact message shows as a benign notice (neutral title, no support prompt) and no home navigation; verify `npx vitest run src/features/connect_league/__tests__/connect-league.steps.test.tsx`

## 4. Docs & sync

- [x] 4.1 Update `docs/db/dynamodb_spec.md` `last_refresh_at` wording to the once-per-week (7-day) semantics
- [x] 4.2 Document the `429` response on `POST /leagues` in `docs/api/openapi_spec.yaml`
- [x] 4.3 Lint/format: `pipenv run ruff check --fix . && pipenv run ruff format .`; from `frontend/`: `npm run lint && npm run format:fix`
- [x] 4.4 Run `openspec validate --all` and confirm it passes
