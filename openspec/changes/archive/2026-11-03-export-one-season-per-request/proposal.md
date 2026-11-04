# Proposal

## Why

Exporting a league with many seasons in a single `GET /leagues/{id}/export` call can produce a
response larger than Lambda's 6 MB synchronous limit. The handler succeeds, but the Lambda runtime
fails to post the response (`413 RequestEntityTooLarge`) and API Gateway returns a generic 500, so
users see an internal server error and get no file. A single season is well under the limit.

## What Changes

- The export dialog requests each selected season in its own export call (bounded concurrency of 3)
  instead of one call carrying every selected season.
- Per-season bundles are merged client-side and downloaded as the same single ZIP as today.
- Failure handling: any season request that fails with an error other than "no data" aborts the
  whole export, shows an inline error, and downloads nothing.
- A season the API reports as having no data (404) is omitted from the ZIP; if every selected
  season is omitted, the dialog shows an inline error instead of downloading an empty ZIP.
- No backend or API contract change: `seasons` remains a comma-separated list and a single season
  is already supported.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `frontend/export-league-data`: the "Download selected seasons as a ZIP of JSON files" and "Surface
  export errors inline" requirements change to specify one request per season, merged into one ZIP,
  with abort-on-failure and omit-on-no-data behavior.

## Impact

- Frontend: `frontend/src/features/export_league/export-league-dialog.tsx` and its jest-cucumber
  tests under `features/export_league/__tests__/`.
- No change to backend code, `docs/api/openapi_spec.yaml`, data model, or architecture diagram.
- Residual risk: a single season larger than 6 MB would still fail; that would need an S3
  presigned-URL approach.
