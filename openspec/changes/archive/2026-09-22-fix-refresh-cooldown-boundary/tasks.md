## 1. Backend cooldown fix (backend/league-refresh)

- [x] 1.1 In `src/api/routes.py` (REFRESH branch), replace the exact-duration cooldown comparison
  with a whole-UTC-calendar-day comparison: reject only when `(now.date() - last_refresh_dt.date())`
  is fewer than `REFRESH_COOLDOWN_DAYS` days; compute the remaining wait to the start (midnight UTC)
  of the next allowed calendar day. Keep `REFRESH_COOLDOWN_DAYS`, `_format_cooldown_wait`, the `429`
  message, and the DEV bypass unchanged.
- [x] 1.2 Update `docs/api/openapi_spec.yaml` `TooManyRequests` description to state the cooldown is
  measured in whole UTC calendar days rather than "less than 7 days old".

## 2. Tests

- [x] 2.1 In `tests/unit/api/test_endpoints.py`, add a boundary test: with a frozen `now`,
  `last_refresh_at` set to 7 UTC calendar days ago but fewer than 7×24h earlier (e.g. now
  `2026-09-22 08:00Z`, last refresh `2026-09-15 10:00Z`) → the refresh proceeds (not `429`).
  Confirm the existing within-cooldown, outside-cooldown, and DEV-bypass tests still pass.

## 3. Validation

- [x] 3.1 `pipenv run ruff check --fix . && pipenv run ruff format .`; run
  `pipenv run pytest tests/unit/api/test_endpoints.py` and
  `pipenv run behave tests/component/features/league_refresh.feature`.
- [x] 3.2 `openspec validate fix-refresh-cooldown-boundary --strict` passes; archive with
  `/opsx:archive` after implementation is complete.
