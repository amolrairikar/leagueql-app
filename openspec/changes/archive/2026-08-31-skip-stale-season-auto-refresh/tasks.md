## 1. Refresher code

- [x] 1.1 `src/sleeper_refresh/utils.py`: change `get_sleeper_leagues()` to accept `current_season: int`; skip a canonical's most-recent selection when `int(best["season"]) < current_season`; skip pending renewals when `int(pending_season) < current_season`; update the docstring.
- [x] 1.2 `src/sleeper_refresh/handler.py`: after the season_type/week gate, read `season` from NFL state, raise if absent/unparseable (indeterminate state), and pass `current_season` to `get_sleeper_leagues`.

## 2. Tests

- [x] 2.1 `tests/unit/sleeper_refresh/test_utils.py`: pass `current_season` to every `get_sleeper_leagues` call; add stale-season-skipped, equal-season-refreshed, stale-pending-skipped, and current/future-pending-polled cases.
- [x] 2.2 `tests/unit/sleeper_refresh/test_handler.py`: add `season` to `get_nfl_state` mocks; add a missing/non-numeric-season-raises test.
- [x] 2.3 `tests/component/features/sleeper_auto_refresh.feature` + `steps/sleeper_refresh_steps.py`: add a seed step with an explicit season and a run step with an explicit NFL season; add a scenario where a league behind the current season (and a stale pending) is not invoked.

## 3. Validate

- [x] 3.1 `pipenv run ruff check --fix . && pipenv run ruff format .`
- [x] 3.2 `pipenv run pytest tests/unit/sleeper_refresh/ --cov=src/sleeper_refresh --cov-report=term-missing`
- [x] 3.3 `pipenv run behave tests/component`
- [x] 3.4 `openspec validate --all`
