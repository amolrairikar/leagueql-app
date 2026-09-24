# Tasks

## 1. Core: per-season resilient validation

- [x] 1.1 Rewrite `validate_api_results` in `src/onboarder/utils.py` to group results by
  season, drop seasons with any `data is None`, `logger.warning` the skipped seasons,
  return only fully-successful seasons' results, raise `RuntimeError` when no season
  survives (all-fail) and still raise on a gathered `BaseException`; verify via updated
  `tests/unit/onboarder/test_utils.py::TestValidateApiResults` cases (keep good season,
  drop failed season, single survivor kept, all-fail raises, `BaseException` raises,
  skip logged).
- [x] 1.2 Restructure `SleeperClient.fetch_all` in `src/onboarder/sleeper_client.py` to
  build draft-pick URLs from the raw main results and call `validate_api_results` once
  over `main + pick` results so a pick failure drops the whole season; verify via a
  `tests/unit/onboarder/test_sleeper_client.py` case where a season's draft-pick fetch
  fails (season dropped) plus an all-success multi-season case (unchanged).

## 2. Record only onboarded seasons

- [x] 2.1 In `OnboardingService.run()` (`src/onboarder/onboarding_service.py`) derive
  `onboarded_seasons` from `raw_data` after the fetch and pass it to
  `write_league_records(seasons=...)`, updating the surrounding log lines to the
  onboarded count; verify via `tests/unit/onboarder/test_onboarding_service.py`
  (`TestOnboardingServiceRun`) asserting `write_league_records` and
  `upload_results_to_s3` receive only the surviving season(s).
- [x] 2.2 Confirm the onboarder handler behavior in
  `tests/unit/onboarder/test_handler.py`: all-seasons-fail still → `502`/`UPSTREAM`
  (existing `test_runtime_error_during_run_records_upstream`), and a partial-success run
  returns `200`.

## 3. Component coverage (onboarder → processor)

- [x] 3.1 Add a small multi-season ESPN fixture under `tests/component/fixtures/espn/`
  (two seasons; ~2 owners, 2 weeks; every DuckDB-referenced table has ≥1 row) and extend
  `_FakeClient` / add a step in `tests/component/steps/onboarding_steps.py` to inject a
  per-season fetch failure (emit a `{"data": None}` entry for one season); verify the new
  step drives `validate_api_results` to drop that season.
- [x] 3.2 Add scenarios to `tests/component/features/onboard_to_processed.feature`:
  (a) one season fails, the other onboards → onboarder `200`, processor
  `JOB_STATUS "COMPLETED"`, good-season SK items present and failed-season SK items
  absent; (b) all seasons fail → `502`, `JOB_STATUS "FAILED"`, no METADATA; verify with
  `pipenv run behave tests/component`.

## 4. Validate & finalize

- [x] 4.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`; verify
  clean.
- [x] 4.2 Run `pipenv run pytest tests/unit/onboarder/ --cov=src/onboarder
  --cov-report=term-missing` (coverage ~100% incl. new branches) and
  `pipenv run behave tests/component`; verify all pass.
- [x] 4.3 Run `openspec validate partial-season-onboarding --strict`; verify the change
  validates.
