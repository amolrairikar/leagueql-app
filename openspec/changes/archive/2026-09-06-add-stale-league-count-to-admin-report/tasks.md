## 1. Aggregation helper

- [x] 1.1 In `src/admin_report/aggregations.py`, add a `_DEFAULT_STALE_DAYS = 365` constant and a pure `count_stale(items, now, days=_DEFAULT_STALE_DAYS)` helper that counts leagues whose reference timestamp — `last_refresh_at`, falling back to `onboarded_at` — is strictly older than `now - days`; a league with neither timestamp parseable is not counted. Add `last_refresh_at` to the module docstring's attribute list.
- [x] 1.2 Add a `TestCountStale` class to `tests/unit/admin_report/test_aggregations.py` covering: empty input; stale via old `last_refresh_at`; fresh via recent `last_refresh_at`; fallback to `onboarded_at` when `last_refresh_at` is absent; a recent `last_refresh_at` overriding an old `onboarded_at` (not stale); the 365-day boundary being exclusive; both timestamps missing/unparseable excluded; a custom `days`.

## 2. Wire into the digest

- [x] 2.1 In `src/admin_report/handler.py`, add a `STALE_DAYS = 365` constant, import `count_stale`, compute `stale = count_stale(items, now, days=STALE_DAYS)` in `_build_embed`, and add a `{"name": "Stale (1y)", ...}` inline field after the `Active` field. Update the module docstring's digest summary to mention the stale count.
- [x] 2.2 Extend `tests/unit/admin_report/test_handler.py` to assert the `Stale (1y)` field renders with the expected count.

## 3. Validate

- [x] 3.1 From repo root: `pipenv run pytest tests/unit/admin_report/ --cov=src/admin_report --cov-report=term-missing`, then `pipenv run ruff check --fix .` and `pipenv run ruff format .`.
- [x] 3.2 `openspec validate --all`.
