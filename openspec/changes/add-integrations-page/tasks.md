# Tasks

## 1. Feature flag

- [x] 1.1 Add `INTEGRATIONS = "integrations"` to `src/common/feature_flags.py` and expose it in the `get_feature_flags` whitelist (`src/api/routes.py`); update `TestFeatureFlagsEndpoint` and the `FeatureFlagsResponse` schema in `docs/api/openapi_spec.yaml`; verify `pipenv run pytest tests/unit/api/test_endpoints.py -k FeatureFlags` passes
- [x] 1.2 Add `isIntegrationsEnabled()` to `frontend/src/lib/feature-flags.ts`; verify `npx vitest run src/lib` passes

## 2. GitHub client and issue format (`src/api/integrations.py`)

- [x] 2.1 Define the shared `IntegrationSubmission` Pydantic model (field limits, category enum, https link, views limited to `EXPORT_SEASON_VIEWS` keys + `teams`) and verify unit tests cover each 422 case
- [x] 2.2 Implement `build_issue_body` / `parse_issue_body` (v1 marker, `###` sections, code-span/fence neutralization) and verify unit tests round-trip every field, neutralize `@mentions`/backticks, and return `None` for missing marker or invalid fields
- [x] 2.3 Implement `create_issue` (single POST, `integration:submitted` label, title `[Integration] <name>`, token from `GITHUB_TOKEN_SSM_PARAM`, repo from `GITHUB_REPO`) and verify unit tests cover success, non-2xx, timeout, and exactly one attempt
- [x] 2.4 Implement `list_approved` (approved label, `state=all`, skip PRs and malformed bodies, newest-featured-only, 5-min cache, stale-on-error) and verify unit tests cover filtering, featured selection, cache hit, stale fallback, and no-cache error

## 3. Endpoints and submission limit

- [x] 3.1 Add the per-user submission limit helper (`USER#<sub>` / `INTEGRATION_SUBMISSIONS`, rolling 24h, record only after success, `ttl`) and document the item in `docs/db/dynamodb_spec.md`; verify unit tests cover under-limit, at-limit 429, window expiry, and failed attempts not counted
- [x] 3.2 Add `GET /integrations` and `POST /integrations` to `src/api/routes.py` (auth, flag-off 404, 201 `{issue_number}`, 429, 502 + `publish_failure`, Clerk id only in logs); verify endpoint unit tests in `tests/unit/api/` pass with coverage near 100%
- [x] 3.3 Add both operations to `docs/api/openapi_spec.yaml` with `ClerkJWT` security and the `x-amazon-apigateway-integration` block; verify the YAML parses and the paths match the routes
- [x] 3.4 Add `tests/component/features/integrations.feature` + steps (GitHub mocked, moto DynamoDB): submit then list shows it only once approved, limit 429, flag off 404; verify `pipenv run behave tests/component/features/integrations.feature` passes

## 4. Infrastructure and docs

- [x] 4.1 Add `GITHUB_TOKEN_SSM_PARAM` and `GITHUB_REPO` to the API Lambda env in `infrastructure/regional/main.tf`; add a `ReadGithubTokenSsmParameter` statement (both regions) to `api-lambda-role` in `infrastructure/global/{dev,prod}/main.tf`; add a `POST /integrations` `route_settings` throttle (burst 1, rate 1) in `infrastructure/modules/api-gw/main.tf`; verify `terraform fmt -check` and `terraform validate` pass
- [x] 4.2 Add GitHub as an external dependency of the API Lambda in `docs/architecture/architecture_diagram.py` and regenerate the PNG; verify the PNG shows the new edge

## 5. Frontend page

- [x] 5.1 Create `frontend/src/features/integrations/{types.ts,constants.ts,api-calls.ts}` (categories + labels, export view names, how-it-works copy, `listIntegrations`, `submitIntegration`); verify `npm run build:ci` type-checks
- [x] 5.2 Build `integrations-page.tsx` + `integration-card.tsx` (header, steps, featured card, chips with counts, search, grid, loading/empty/no-matches/error states) and add `__tests__/integrations-page.feature` + steps covering render, featured/no featured, empty, 5xx error, filter, search, no matches; verify `npx vitest run src/features/integrations` passes
- [x] 5.3 Build `integration-detail-dialog.tsx` (steps, `<season>_<view>.json` files, external link, conditional prompt + Copy → Copied) and add scenarios for open details, copy prompt, and no prompt; verify the vitest run passes
- [x] 5.4 Build `submit-integration-dialog.tsx` (all fields, AI-prompt hint to put the prompt in setup steps, in-flight disable, success, 4xx message, 5xx retry message, values kept on failure) and add `__tests__/submit-integration.feature` + steps for success, 429, 502, and the AI-prompt hint; verify the vitest run passes
- [x] 5.5 Register `/integrations` in `APP_LAYOUT_ROUTES` (redirect to `/home` when the flag is off) and add the "Community" sidebar group; extend the sidebar gating test for flag on/off; verify `npx vitest run src/features/sidebar src/features/integrations` passes

## 6. Integration checks

- [x] 6.1 Run `pipenv run ruff check --fix . && pipenv run ruff format .`, `npm run format:fix && npm run lint`, the full unit, component, and frontend suites, and `openspec validate --all`; verify all pass
- [ ] 6.2 After the manual setup (PAT, SSM parameter, labels, flag JSON) and a dev deploy with the flag on: submit an integration, approve it, feature it, remove approval, hit the daily limit, and turn the flag off; verify each behaves as the specs describe
