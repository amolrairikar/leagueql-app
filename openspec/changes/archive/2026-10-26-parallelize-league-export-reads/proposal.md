# Proposal

## Why

`GET /leagues/{leagueId}/export` (`src/api/routes.py`) reads every requested season's views one
after another: seasons × views sequential DynamoDB round trips, each prefix view paginating
serially. For a league with many seasons that is dozens of serial calls inside an API Lambda with a
15 s timeout, so a large export is the endpoint most likely to approach the limit and fail with a
timeout.

## What Changes

- Issue the per-season, per-view DynamoDB reads concurrently on a bounded worker pool instead of
  serially, producing the identical response body.
- Make the contract explicit that a failed read fails the whole export (`500`, no partial bundle)
  and that the bundle does not depend on the order reads complete in.
- Keep OpenTelemetry trace context flowing into the worker threads so DynamoDB spans stay children
  of the request span.

## Capabilities

### New Capabilities

### Modified Capabilities
- `backend/league-export`: adds requirements that the bundle is deterministic regardless of read
  completion order and that any failed view read fails the whole export.

## Impact

- `src/api/routes.py` (`export_league`), possibly a small helper in `src/api/helpers.py`.
- Tests: backend unit tests (`tests/unit/api/`) for concurrency, ordering, and error propagation;
  backend component scenario in `tests/component/features/api_export.feature`.
- No API contract, data model, infrastructure, or frontend changes, so `docs/api/openapi_spec.yaml`
  and `docs/db/dynamodb_spec.md` are unaffected. Read capacity consumed is unchanged; only its
  timing is compressed.
