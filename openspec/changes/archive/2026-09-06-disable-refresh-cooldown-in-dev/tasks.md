## 1. Backend — cooldown gate

- [x] 1.1 In `src/api/routes.py`, guard the cooldown block (the `if last_refresh_at:` at ~line 278) so it is skipped when `os.environ.get("ENVIRONMENT") == "dev"` — e.g. `if last_refresh_at and os.environ.get("ENVIRONMENT") != "dev":`. Leave the in-progress `409` and up-to-date `409` guards untouched. `os` is already imported.

## 2. Backend — tests

- [x] 2.1 In `tests/unit/api/test_endpoints.py`, ensure `test_refresh_returns_429_when_within_cooldown` (:473) runs with `ENVIRONMENT` set to a non-dev value (monkeypatch to `"prod"`) so it still exercises the `429` path; verify it passes.
- [x] 2.2 Add a unit test asserting that with `ENVIRONMENT=dev` a within-cooldown refresh proceeds (no `429`). Confirm `test_refresh_proceeds_when_outside_cooldown` (:491) still passes.
- [x] 2.3 Set `ENVIRONMENT="prod"` in the component harness `_ENV` (`tests/component/environment.py`) so the cooldown scenario is deterministic regardless of the shell env. A component dev-bypass scenario was intentionally NOT added: after skipping the cooldown, the refresh reaches `get_nfl_state()`, which makes a live Sleeper HTTP call not mocked at that step, so a `201` assertion would be non-deterministic. The dev bypass is fully covered by the unit test in 2.2.

## 3. Verify

- [x] 3.1 Run `pipenv run ruff check --fix . && pipenv run ruff format .` (lint/format clean).
- [x] 3.2 Run `pipenv run pytest tests/unit/api/test_endpoints.py` and `pipenv run behave tests/component` (green — 151 unit, 56 component scenarios).
- [x] 3.3 Run `openspec validate --all` (passes, no dangling references).
