# Tasks

## 1. Read the triggering manifest version

- [x] 1.1 In `src/processor/handler.py`, read `versionId` from the S3 event record and pass it to `get_object(..., VersionId=...)` when present (latest object otherwise). Verify with unit tests in `tests/unit/processor/test_handler.py` asserting `get_object` is called with the event's `VersionId`, and without it when the event has none.
- [x] 1.2 Give `get_previous_version_id` an optional `version_id` and return the version immediately older than it (None when it is the oldest or not listed), keeping the second-newest behavior when it is omitted. Verify with unit tests covering triggering-is-latest, triggering-is-older, oldest, not-listed, and no-version-id.

## 2. End-to-end race coverage

- [x] 2.1 Add a component scenario where a Yahoo backfill writes the manifest with `reprocess_all`, the manifest is then copied with `reprocess_seasons` before the processor runs, and the processor (invoked with the first version's event) rebuilds every season and records the backfill's JOB_STATUS. Verify with `pipenv run behave tests/component`.

## 3. Integration checks

- [x] 3.1 Run `pipenv run ruff check --fix . && pipenv run ruff format .`, `pipenv run pytest tests/unit`, `pipenv run behave tests/component` and `npx @fission-ai/openspec@latest validate --all`, and verify all of them pass.
