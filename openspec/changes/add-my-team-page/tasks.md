# Tasks

## 1. Backend: user league preferences

- [x] 1.1 Add helpers in `src/api/helpers.py`: `get_user_league_prefs(canonical_id, clerk_user_id)` reads `SK=USER#{id}`, and `put_user_league_prefs(...)` upserts `owner_id` + `updated_at`. Add `league_has_owner(canonical_id, owner_id)` to check `TEAMS` `primary_owner_id` across all seasons. Verify with new unit tests in `tests/unit/api/test_utils.py`, covering a hit, a miss and a ClientError → 500.
- [x] 1.2 Add `GET` and `PUT /leagues/{leagueId}/me` to `src/api/routes.py`: `get_authenticated_user` → `lookup_league` (404) → `get_league_metadata` → `require_league_member` (403) → read/validate (400)/write, with a `{"owner_id": str | null}` response and `Cache-Control: no-store`. Verify with unit tests in `tests/unit/api/test_endpoints.py` for 200 null, 200 round-trip, change claim, 400 unknown owner (stored claim unchanged), 401, 404, 403 for an ESPN/Yahoo non-member, and Sleeper open.
- [x] 1.3 Add a Behave scenario pair `tests/component/features/api_user_prefs.feature` + steps (in `api_steps.py`, or a new steps file) against moto DynamoDB: claim, read back, per-user isolation, and league delete removing the `USER#` item. Verify `pipenv run behave tests/component/features/api_user_prefs.feature` passes.
- [x] 1.4 Document the endpoints in `docs/api/openapi_spec.yaml` (with the same JWT authorizer and Lambda integration blocks as sibling routes, since this file generates API Gateway), and the `USER#` item in `docs/db/dynamodb_spec.md`. Verify the YAML parses (`python -c "import yaml;yaml.safe_load(open('docs/api/openapi_spec.yaml'))"`) and the new paths appear.
- [x] 1.5 Add `PUT` to the CORS allowed methods in `infrastructure/modules/api-gw/main.tf` and `src/api/main.py`, and verify with a unit test that an `OPTIONS` preflight for `PUT` returns `PUT` in `access-control-allow-methods`.
- [x] 1.6 Run `pipenv run ruff check --fix . && pipenv run ruff format .` and `pipenv run pytest tests/unit/api`, and verify all pass with the new code fully covered.

## 2. Frontend: data and calculations

- [x] 2.1 Create `frontend/src/features/my_team/api-calls.ts` with `getMyTeam` / `putMyTeam` (typed `{ owner_id: string | null }`), and stub `/me` in `lib/demo-api.ts` (GET → first demo owner, PUT → echo). Verify with `npm run build:ci` type-checks.
- [x] 2.2 Create `frontend/src/features/my_team/compute-my-team.ts`, a pure function that takes season matchups, all-season matchups, `migrationMapping`, league settings and the claimed owner, and returns:
  - the current/last week and offseason flag (design decision 8)
  - the claimed team + opponent
  - last-week result
  - record/rank/PF
  - odds now and the odds change (design decision 6)
  - season efficiency + last week's bench points (design decision 7)
  - H2H, last meeting and the opponent's last 3
  - the preview (projected score, win probability)
  - the award count and latest award

  Verify with Vitest unit tests (`__tests__/compute-my-team.test.ts`) covering mid-season, Week 1, offseason, a playoff bye (no matchup), a migrated owner id, and parity against `buildMatchupPreview` / `computePlayoffOdds` / `computeStartSitReport` outputs.

## 3. Frontend: page, route and sidebar

- [x] 3.1 Build `my-team.tsx` with a skeleton, an inline `<ErrorAlert>` for claim and data failures, the claim picker ("Save my team" / "Not now", inline error on save failure), and the Your week card matching the mockup: tiles, matchup panel with a link to `/matchups`, awards row, disabled "Email me each week" row with "COMING SOON!", and "Change team". Verify with the jest-cucumber pair `__tests__/my-team.feature` + `my-team.steps.test.tsx` (MSW), with scenarios for every requirement in `specs/frontend/my-team/spec.md`, including demo mode and the non-operable email switch.
- [x] 3.2 Register `/my_team` in `frontend/src/app/app.tsx` (no feature flag). Verify with the my-team feature, whose scenarios open the page at `/my_team`.
- [x] 3.3 Add the "My Team" entry after "Home" in `features/sidebar/app-sidebar.tsx` (always shown). Verify with `__tests__/my-team-nav.feature` + steps: the entry sits between Home and Standings and links to `/my_team`.
- [x] 3.4 From `frontend/`, run `npm run format:fix && npm run lint && npx vitest run src/features/my_team src/features/sidebar && npm run build:ci` and verify all pass.
- [x] 3.5 Add "My top 3 draft picks": load the current season's `DRAFT` view (a failure falls back to no picks), select the claimed team's top 3 picks by VORP (excluding null VORP), and render them on the in-season and offseason cards. Verify with unit tests in `compute-my-team.test.ts` (ordering, null exclusion, fewer than three, other teams' picks ignored) and my-team feature scenarios (list shown; empty and failed loads show "No draft value data yet").

## 4. Integration

- [x] 4.1 Run `npx @fission-ai/openspec@latest validate --all`, the full `pipenv run pytest tests/unit`, `pipenv run behave tests/component`, and `npm run test`, and verify all green.
- [ ] 4.2 Manually, in dev: claim a team on a Sleeper league, and check the card's numbers against `/matchups` (preview), the playoff predictor (odds), and the box-score efficiency chip for last week.
