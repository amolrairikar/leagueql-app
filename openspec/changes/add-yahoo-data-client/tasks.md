## 1. Prerequisite: archive the OAuth linking change

- [x] 1.1 Archive `add-yahoo-league-support` (`/opsx:archive`) so `backend/yahoo-oauth` and
  `frontend/connect-yahoo-league` become live specs; verify `openspec list --specs` lists both and
  `openspec validate add-yahoo-data-client` no longer reports dangling delta references.

## 2. Shared token module (refactor, no behavior change)

- [x] 2.1 Create `src/common/yahoo_tokens.py` with a dependency-injected `YahooTokenClient`
  (encrypt/decrypt, refresh, store, get_valid_access_token) plus `from_env()` building a KMS client
  pinned to `YAHOO_KMS_REGION`; move the engine out of `src/api/yahoo_oauth.py`. Verify
  `pipenv run pytest tests/unit/common/test_yahoo_tokens.py`.
- [x] 2.2 Re-import/delegate the moved names in `src/api/yahoo_oauth.py` so its public surface is
  unchanged; verify `pipenv run pytest tests/unit/api/test_yahoo_oauth.py
  tests/unit/api/test_yahoo_endpoints.py` still pass unmodified (authorize/callback identical).

## 3. Yahoo data client (per-league data only; no player scoring)

- [x] 3.1 Add `src/onboarder/yahoo_client.py` with `__init__(league_id, owner_user_id, is_refresh)`
  and a sync `get_seasons()` that enumerates the owner's NFL leagues
  (`/users;use_login=1/games;game_codes=nfl/leagues`), resolves the entered league id → `league_key`,
  verifies membership, and walks the `renew` chain (current season only when `is_refresh`), storing
  the season→`league_key` map. Verify unit tests cover full-history, refresh, and not-a-member cases.
- [x] 3.2 Implement `async fetch_all()` returning `{"season","data_type","data"}` records for
  settings/standings/teams/matchups(per week from settings)/draftresults/transactions, using
  `run_fetches`/`fetch_with_retry` with a Bearer header from `common.yahoo_tokens` and `?format=json`;
  paginate transactions with `start=`; refresh the token on 401. Verify unit tests with canned Yahoo
  JSON + a mocked token provider (incl. pagination and mid-run refresh).
- [x] 3.3 Add Yahoo per-type filter functions (`_YAHOO_DATA_FILTERS`) that flatten Yahoo's
  numeric-keyed JSON into the grouped shapes the processor expects — members+teams (with managers),
  settings, standings, matchups, draft_picks (player_key), transactions (player_key). Verify filter
  unit tests assert the normalized shapes.

## 4. Yahoo player-data ECS refresher (service credential)

- [x] 4.1 Add `src/yahoo_player_stats_refresher/` (Dockerfile + `main()` + `requirements.txt`,
  mirroring `src/sleeper_player_stats_refresher/`) that authenticates with the service token
  (service account resolved from SSM via `YAHOO_SERVICE_USER_ID_SSM_PARAM`, using
  `common.yahoo_tokens`), paginates `players;out=metadata,stats`
  (25/page), and writes `player-metadata/yahoo_nfl_players.json` + `player-stats/yahoo_nfl_player_stats.json`
  to S3, deep-merging stats and honoring `SEASON`/`MAX_PLAYERS`/`OUTPUT_KEY` overrides. Verify
  `pipenv run pytest tests/unit/yahoo_player_stats_refresher/`.

## 5. Onboarder wiring

- [x] 5.1 Add a `YAHOO` branch to `OnboardingService._build_client`
  (`src/onboarder/onboarding_service.py`) returning `YahooClient(league_id, owner_user_id, is_refresh)`,
  threading `owner_user_id` into `_build_client` and updating the return-type union/docstring. Verify
  `pipenv run pytest tests/unit/onboarder/test_onboarding_service.py`.

## 6. Processor transforms

- [x] 6.1 Add `_register_yahoo_raw_data(raw_data, player_metadata, player_stats)` in
  `src/processor/handler.py` producing the same grouped keys as `_register_espn_raw_data` (members,
  teams, matchups, brackets via `_build_yahoo_brackets`, draft_picks, player_scoring_totals from the
  cache, transactions, league_name_by_season, league_settings_by_season via `build_league_settings_row`);
  wire the `elif platform == "YAHOO"` branch in `register_raw_data` and load the Yahoo player-data
  caches from S3 (mirroring the Sleeper `player-metadata`/`player-stats` reads, tolerating absence).
  Verify processor unit tests.
- [x] 6.2 Add `"YAHOO"` sub-keys under `TEAMS`, `MATCHUPS`, `PLAYOFF_BRACKET`, `DRAFT`, and
  `TRANSACTIONS` in `src/processor/queries.py`; extend `_EMPTY_VIEW_DTYPES` if any Yahoo view can be
  legitimately empty. Verify the YAHOO transforms produce views matching the ESPN/Sleeper schema in
  unit tests.

## 7. API onboard path

- [x] 7.1 Replace the `YAHOO_COMING_SOON` block in `onboard_league` (`src/api/routes.py`) with the
  real path: keep the `has_valid_link` 403 gate, then `lookup_league(platform=YAHOO)`, the
  onboarded/refresh checks, `create_job_status`, `set_active_job`, and `invoke_onboarder` (no
  s2/swid). Gate a Yahoo `REFRESH` on a valid link. Verify
  `tests/unit/api/test_yahoo_endpoints.py::TestYahooOnboardGate` asserts a real invoke.

## 8. Frontend

- [x] 8.1 Update `frontend/src/features/connect_league/yahoo-connect-return.tsx` (and the
  `YAHOO_COMING_SOON` handling in `api-calls.ts`) so a linked league onboards and polls to completion
  (reuse `poll.ts`), keeping the 403/`YAHOO_AUTH` reconnect path. Verify the updated
  `__tests__/yahoo-connect.steps.test.tsx` (MSW-mocked onboarding + polling) passes via `npx vitest run`.

## 9. Infra

- [x] 9.1 Give the onboarder Lambda the Yahoo env vars (`YAHOO_KMS_KEY_ID`, `YAHOO_KMS_REGION`,
  `YAHOO_CLIENT_ID_SSM_PARAM`, `YAHOO_REDIRECT_URI`) in `infrastructure/regional/main.tf`, and extend
  the `EncryptDecryptYahooTokens` KMS + `ReadYahooClientIdSsmParameter` SSM grants to the onboarder
  role in `infrastructure/global/{dev,prod}/main.tf`. Verify `terraform validate`/`terraform fmt -check`.
- [x] 9.2 Add the Yahoo player-data ECS Fargate task (task definition, image, schedule, and
  `YAHOO_SERVICE_USER_ID_SSM_PARAM` + `YAHOO_SERVICE_LEAGUE_KEY_SSM_PARAM` + Yahoo env), with its
  role granted S3 write, KMS decrypt, SSM read, and
  DynamoDB read on the token item — mirroring the Sleeper stats task. Verify `terraform validate`.

## 10. Component tests

- [x] 10.1 Add `tests/component/fixtures/yahoo/raw_data_*.json` (+ Yahoo `player_metadata`/
  `player_stats` fixtures) and drive onboarding through the existing `_FakeClient` seam in
  `tests/component/steps/onboarding_steps.py`; add Yahoo scenarios to
  `features/onboard_to_processed.feature`. Verify `pipenv run behave tests/component`.

## 11. Docs & diagram

- [x] 11.1 Add `YAHOO` to the platform enum error text in `docs/api/openapi_spec.yaml` and to the
  `platform`/`active_platform`/`migrated_from` enums in `docs/db/dynamodb_spec.md`. Verify the enum
  strings include YAHOO.
- [x] 11.2 Add the Yahoo Fantasy API integration, the onboarder→Yahoo edge, and the new Yahoo
  player-data ECS task in `docs/architecture/architecture_diagram.py`; regenerate the PNG
  (`pipenv run python docs/architecture/architecture_diagram.py`). Verify the PNG updates.

## 12. Full verification

- [x] 12.1 Lint/format clean (`pipenv run ruff check --fix . && pipenv run ruff format .`;
  `npm run format:fix && npm run lint` in `frontend/`); `openspec validate --all` green; full backend
  unit + component suites and the connect_league vitest suite pass.
- [ ] 12.2 DEV end-to-end with a real linked Yahoo account: run the player-data task once, then
  landing page → pick Yahoo → enter league id → Connect → OAuth → job polls to COMPLETED and
  standings/matchups/draft/transactions render; then a `REFRESH` succeeds.

## 13. Fixes from DEV verification (task 12.2)

- [x] 13.1 Fix Yahoo sub-collection parsing: real Yahoo returns a team's `managers`/`team_logos` as
  plain lists, but `_collection_items(_flatten(...))` only handled the numeric-keyed shape, so every
  owner id/display name/logo parsed to null. Make `_collection_items`
  (`src/common/yahoo_members.py`) accept a plain list and drop the pre-`_flatten` at the
  managers/logos call sites in `_filter_teams` (`src/onboarder/yahoo_client.py`) and
  `parse_managers` (`src/common/yahoo_members.py`). Correct the unit-test fixtures (which used the
  wrong numeric-keyed shape) to the real list shape and add plain-list coverage.
- [x] 13.2 Make the Yahoo `TEAMS` transform resilient: replace the reused ESPN `TEAMS` query (INNER
  JOIN members) with a Yahoo-specific query that LEFT JOINs members, so a team with no resolvable
  manager still yields a `teams_output` row instead of emptying every dependent view. Add a
  processor regression test.
- [x] 13.3 Fix collapsing managers: Yahoo masks the manager `guid` in some (e.g. public) leagues,
  returning the SAME value for every team, so keying owners on `guid or manager_id` deduped all
  members to one and every team showed a single manager in the UI. Add
  `resolve_team_owner_ids`/`_primary_manager` in `src/common/yahoo_members.py` that use the guid only
  when present for every team AND distinct, else fall back to the per-league `manager_id`; use it in
  `_filter_teams` (`src/onboarder/yahoo_client.py`) and `parse_managers`. Add unit tests for masked,
  distinct, and partial-guid cases.
