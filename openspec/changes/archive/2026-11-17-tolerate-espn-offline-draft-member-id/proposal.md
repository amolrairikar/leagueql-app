## Why

ESPN only attaches `memberId` to draft picks made in a live draft. A league with a commissioner-entered (offline) draft returns picks without it, so the processor's ESPN `DRAFT` transform (`ds.memberId AS member_id`) fails with a DuckDB `BinderException` and the whole onboarding job fails — no league data is written.

## What Changes

- ESPN draft picks lacking `memberId` are given `memberId = null` before registration, so the `DRAFT` view binds and is written with a null `member_id`.
- The frontend `DraftPickItem.member_id` type becomes `string | null` (no view reads it); the data-model doc notes the null cases.

## Capabilities

### Modified Capabilities
- `backend/data-processing-pipeline`: tolerate ESPN draft picks that omit `memberId`.

## Impact

`src/processor/handler.py`, processor unit tests, an ESPN offline-draft component scenario + fixture, `frontend/src/features/draft_grades/api-calls.ts` (type only), `docs/db/dynamodb_spec.md`.
