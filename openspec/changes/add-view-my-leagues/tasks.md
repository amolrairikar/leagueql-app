# Tasks

## 1. Infrastructure and data model docs

- [x] 1.1 Add `member_user_id` and `joined_at` attribute definitions and a `GSI4` (HASH `member_user_id`, RANGE `joined_at`, `KEYS_ONLY`) to `infrastructure/modules/dynamodb/main.tf`; verify with `terraform validate` / `terraform fmt -check`
- [x] 1.2 Add `index/GSI4` (primary + replica) to the API Lambda DynamoDB policy in `infrastructure/global/prod/main.tf`; verify with `terraform validate`
- [x] 1.3 Document the MEMBER item and GSI4 in `docs/db/dynamodb_spec.md` (table overview GSIs row, key schema section, items section); verify by reviewing the rendered markdown
- [x] 1.4 Add GSI4 to the moto table definitions used by tests (`tests/component/environment.py` and unit fixtures that build the table with GSI3); verify the existing suites still pass with `pipenv run pytest tests/unit -q` and `pipenv run behave tests/component`

## 2. Membership index writes

- [x] 2.1 Add a shared helper that does the idempotent conditional put of a `MEMBER#{uid}` row (swallowing `ConditionalCheckFailedException`), with unit tests for created, already exists, and other ClientError
- [x] 2.2 Onboarder: add the owner row `Put` to the first-onboard `transact_items` in `src/onboarder/writer.py` only when `owner_user_id` is set; update writer unit tests (with owner → row present; system onboard → absent; refresh path → no row put)
- [x] 2.3 `add_league_member` (accept-invite) also writes the caller's row; unit tests cover success, idempotent re-redeem, and row-write failure → `500`
- [x] 2.4 `claim-ownership` writes the new owner's row after the METADATA update; unit tests cover success and row-write failure
- [x] 2.5 `get_league` best-effort writes the caller's row when the effective platform is Sleeper (after the member gate); unit tests cover new row, existing row, swallowed error with `200` intact, and no write for ESPN/Yahoo
- [x] 2.6 Backend component scenarios (Behave + moto): onboard → owner row; accept-invite → member row; claim → new owner row while old owner keeps theirs; Sleeper open → row; delete-league → all rows gone; verify with `pipenv run behave tests/component`

## 3. `GET /me/leagues`

- [x] 3.1 Implement the listing helper (GSI4 query with pagination → BatchGetItem METADATA with UnprocessedKeys retry → GSI1 lookup selection → entry assembly → sort) and the authenticated `GET /me/leagues` route with `Cache-Control: no-store`; unit tests cover empty, multiple sorted, migrated ESPN→Sleeper, Sleeper renewals plus pending season, never-refreshed, missing METADATA skipped, and the re-auth flag (owner true / member false / not auto-refreshed false)
- [x] 3.2 Add `/me/leagues` (200 schema, 401, 500) to `docs/api/openapi_spec.yaml` with `security: ClerkJWT` and the Lambda `x-amazon-apigateway-integration` (this generates the API Gateway route); verify the YAML parses and `terraform validate` passes for the regional stack
- [x] 3.3 Component scenarios for `GET /me/leagues` (lists after onboard and invite, empty list, 401 unauthenticated); verify with `pipenv run behave tests/component`
- [x] 3.4 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`, then the full `pipenv run pytest tests/unit` suite

## 4. Backfill script

- [x] 4.1 Add `scripts/utility_scripts/backfill_league_members.py` (GSI3 scan of METADATA → conditional puts for the owner plus `members`, `joined_at = onboarded_at`, prints created/skipped counts) with unit tests for create, re-run idempotency, and leagues with no owner

## 5. Frontend

- [x] 5.1 Add `getMyLeagues()` and the `MyLeague` type in `frontend/src/components/api/leagues.ts`
- [x] 5.2 Build `frontend/src/features/landing_page/my-leagues.tsx` (list rows with platform logos, skeleton, empty state with Connect action, inline `<ErrorAlert>` with retry, missing-league hint, row click → `getLeague` → `setLeagueCookies` → `/home`, inline open error), matching the mockup
- [x] 5.3 Wire the signed-in-only "View My Leagues" button (count pill, `aria-expanded`) into `landing-page.tsx`, mutually exclusive with the Connect form
- [x] 5.4 Add `__tests__/my-leagues.feature` + `my-leagues.steps.test.tsx` (MSW) covering: hidden when signed out, expand/collapse, loaded rows and order, migrated note, re-auth flag, loading, empty → Connect form, 4xx/5xx with retry, row click navigates with cookies set, open failure stays on `/`, mutual exclusion; verify with `npx vitest run src/features/landing_page`
- [x] 5.5 Add the `1.13.0` release (Added: View My Leagues) at the top of `frontend/src/features/changelog/constants.ts` (append to it instead if it already exists); verify the changelog page tests still pass
- [x] 5.6 Run `npm run format:fix`, `npm run lint`, and `npm run build:ci` in `frontend/`

## 6. Integration checks

- [x] 6.1 `npx @fission-ai/openspec@latest validate --all` passes
- [x] 6.2 Full suites green: `pipenv run pytest tests/unit`, `pipenv run behave tests/component`, `npm run test` in `frontend/`
