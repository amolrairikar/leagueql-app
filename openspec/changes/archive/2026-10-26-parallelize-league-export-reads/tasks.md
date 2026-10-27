# Tasks

## 1. Concurrent reads in the export

- [x] 1.1 In `src/api/routes.py` `export_league`, fan the `(season, view)` `read_view` calls out over a `ThreadPoolExecutor(max_workers=8)` with each task run in `contextvars.copy_context()`, then assemble the bundle in the original season/view order; verify the existing export unit and component tests still pass
- [x] 1.2 Add backend unit tests in `tests/unit/api/` for: identical output to the serial result, ordering preserved when later-season reads finish first, a `ClientError`/`HTTPException` from one read producing `500` with no partial bundle, and the request's trace context being visible inside a worker; verify with `uv run pytest tests/unit/api -k export` (no real boto3 at module top level, per tests/CLAUDE.md)
- [x] 1.3 Add a Behave scenario in `tests/component/features/api_export.feature` (+ steps) exporting several seasons with chunked transactions and per-week matchups under `moto`, asserting the full bundle; verify with `uv run behave tests/component --include api_export`

## 2. Quality

- [x] 2.1 Run `uv run ruff check --fix .` and `uv run ruff format .` and verify both are clean
- [x] 2.2 Run `uv run pytest tests/unit` and `uv run behave tests/component` and verify green, then `npx @fission-ai/openspec@latest validate --all` with no errors
