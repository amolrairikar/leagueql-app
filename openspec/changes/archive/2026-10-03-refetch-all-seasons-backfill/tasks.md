# Tasks

## 1. Invoke contract

- [x] 1.1 Add `refetch_all: bool = False` to `invoke_onboarder` in `src/common/onboarder_invoke.py`, sent as the `refetchAll` payload field; verify with `tests/unit/common/test_onboarder_invoke.py` that the field defaults to false and is forwarded when true

## 2. Onboarder

- [x] 2.1 In `src/onboarder/onboarding_service.py`, add a `refetch_all` constructor argument; when it is true, build the platform client with `is_refresh=False`; verify with `tests/unit/onboarder/test_onboarding_service.py`
- [x] 2.2 In `src/onboarder/handler.py`, pass `refetch_all` from `event["refetchAll"]` only for `REFRESH`, and set `reprocess_all` when `refetch_all` is true; verify with `tests/unit/onboarder/test_handler.py` that the field is forwarded on REFRESH and ignored on ONBOARD and MIGRATE

## 3. Backfill script

- [x] 3.1 Add `--refetch-all` to `scripts/utility_scripts/backfill_leagues.py`, forward it to `invoke_onboarder`, show the mode in dry-run output and the confirmation prompt, and update the docstring; verify with `tests/unit/scripts/test_backfill_leagues.py`

## 4. Component coverage

- [x] 4.1 Add a `tests/component/features/league_refresh.feature` scenario in which a refetch-all REFRESH builds the client with the full history, rewrites every season's raw file, rebuilds every season's views without duplicates, and leaves METADATA owner and members unchanged

## 5. Checks

- [x] 5.1 Run `pipenv run ruff check --fix .`, `pipenv run ruff format .`, `pipenv run pytest tests/unit`, and `pipenv run behave tests/component`; verify everything passes
- [x] 5.2 Run `npx @fission-ai/openspec@latest validate refetch-all-seasons-backfill --strict`; verify it passes
