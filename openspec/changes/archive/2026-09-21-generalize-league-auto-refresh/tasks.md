# Tasks

## 1. Rename + generalize the source module

- [x] 1.1 Move `src/sleeper_refresh/` → `src/league_refresh/` (handler.py, utils.py) and verify the package imports resolve (`pipenv run python -c "import importlib"` load, or the unit suite in task 4)
- [x] 1.2 In `utils.py`, replace `get_sleeper_leagues` with `get_leagues_to_refresh(current_season)` that queries `GSI2` once per platform (`SLEEPER`, `YAHOO`), reuses the group-by-canonical / most-recent-season / stale-season logic, and returns dicts with `platform`, `league_id`, `canonical_league_id`, `owner_user_id`; keep Sleeper pending-renewal polling (Sleeper only, `owner_user_id=None`). Verify with new unit tests in task 4
- [x] 1.3 In `utils.py`, for Yahoo canonicals `GetItem` the `METADATA` item (`PK=LEAGUE#{canonical}, SK=METADATA`) to read `owner_user_id`, skipping (with a log) any without one. Verify with the "owner absent → skipped" unit test in task 4
- [x] 1.4 Generalize `invoke_onboarder_lambda(...)` to accept `platform` and `owner_user_id` and pass both through `invoke_onboarder(...)` (body `platform`, `owner_user_id`, still `request_type="REFRESH"` + `canonical_league_id`). Verify the invoke-payload unit tests in task 4 assert `platform` + `ownerUserId`
- [x] 1.5 Add pacing helpers reading `REFRESH_DISPATCH_INTERVAL_SECONDS` (default 3) and `REFRESH_DISPATCH_JITTER_SECONDS` (default 5) → sleep `interval + random.uniform(0, jitter)`. Verify via the pacing unit tests in task 4
- [x] 1.6 In `handler.py`, generalize logging/tracing names (`init_tracing("leagueql-league-refresh")`, `traced_handler("league_refresh.league", …)` + `platform` span attr), call `get_leagues_to_refresh`, group by platform, dispatch with a sleep between consecutive same-platform dispatches (none after a platform's last), keep success/failure counting + raise-if-any-failed and NFL-state gating verbatim. Verify with the handler unit tests in task 4

## 2. Infrastructure

- [x] 2.1 In `infrastructure/regional/main.tf`, rename `sleeper_refresh_lambda` module → `league_refresh_lambda` (`function_name` → `leagueql-league-refresh-${env}`, `s3_key` → `.../league_refresh-lambda.zip`), add `REFRESH_DISPATCH_INTERVAL_SECONDS`/`REFRESH_DISPATCH_JITTER_SECONDS` env vars, and raise `timeout` 60 → 900. Verify `terraform validate` passes
- [x] 2.2 Rename the EventBridge rule/target/permission (`sleeper_refresh_*` → `league_refresh_*`, same cron) and the `sleeper_refresh_errors` alarm → `league_refresh_errors` (update the alarm's function-name dimension + description). Verify `terraform validate`
- [x] 2.3 In `infrastructure/global/{prod,dev}/main.tf`, rename `sleeper-refresh-lambda-role` module → `league-refresh-lambda-role` (`role_name` → `leagueql-${env}-league-refresh-role`, log-group ARNs → `leagueql-league-refresh-${env}`) and add `dynamodb:GetItem` to the DynamoDB statement's actions. Verify `terraform validate`
- [x] 2.4 In `.github/workflows/build.yaml` (line ~277), change `./src/sleeper_refresh` → `./src/league_refresh` in the `build_lambda_zip.sh` args. Verify the path matches the new module directory

## 3. Docs

- [x] 3.1 Update `docs/architecture/architecture_diagram.py` to relabel the refresher node (Sleeper → general league refresher) and regenerate the PNG (`pipenv run python docs/architecture/architecture_diagram.py`). Verify the PNG regenerates without error
- [x] 3.2 Grep docs (`docs/db/dynamodb_spec.md`, `docs/api/openapi_spec.yaml`) for "Sleeper refresh" wording and update any that names the now-general job. Verify no stale Sleeper-only refresher references remain

## 4. Tests

- [x] 4.1 Rename `tests/unit/sleeper_refresh/` → `tests/unit/league_refresh/` (keep `__init__.py`; update `conftest.py` importlib module names). Verify `pipenv run pytest tests/unit/league_refresh` collects
- [x] 4.2 Update `test_utils.py`/`test_handler.py` for the generalized names and add Yahoo cases (GSI2 `platform="YAHOO"` enumeration, METADATA owner resolution, skip-when-owner-absent, invoke payload asserts `platform:"YAHOO"` + `ownerUserId`) and pacing cases (sleep called between same-platform dispatches, not after the last, bounded by interval+jitter — patch `time.sleep`/`random`). Verify `pipenv run pytest tests/unit/league_refresh` passes
- [x] 4.3 Rename `tests/component/features/sleeper_auto_refresh.feature` → `league_auto_refresh.feature` and `steps/sleeper_refresh_steps.py` accordingly (update `tests/component/environment.py` refs); add a Yahoo scenario (seed YAHOO LEAGUE_LOOKUP + METADATA with owner, assert onboarder invoked with that `ownerUserId` + `platform:"YAHOO"`) and a no-owner-skip scenario; patch `time.sleep` in steps. Verify `pipenv run behave tests/component`
- [x] 4.4 Update `tests/integration/sleeper/` (`sleeper_refresh.feature`, `steps/sleeper_refresh_steps.py`, `environment.py`) module/handler references to the renamed module. Verify `pipenv run behave tests/integration/sleeper` stays green

## 5. Validation

- [x] 5.1 Run `pipenv run ruff check --fix . && pipenv run ruff format .`; verify clean
- [x] 5.2 Run the full unit suite `pipenv run pytest` to confirm the rename didn't break cross-imports (e.g. `test_tracing.py`, `test_writer.py` referenced the old name); verify green
- [x] 5.3 Run `openspec validate --all`; verify the change and specs validate
