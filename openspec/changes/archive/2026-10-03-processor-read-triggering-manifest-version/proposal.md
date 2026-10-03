# Proposal

## Why

A Yahoo backfill (`reprocess_all`) can rebuild only the latest season. Every Yahoo refresh also
queues the lineup backfill, which copies `manifest.json` onto itself with replaced metadata
(`reprocess_seasons=<season>`) within seconds. The processor reads the **latest** manifest instead
of the version whose `ObjectCreated` event invoked it. When that copy lands first, the
onboarder-triggered run picks up the lineup backfill's metadata. It loses `reprocess_all` and its
`correlation_id`, and its "previous manifest" is also wrong. The run that should rebuild every
season rebuilds one instead, and its JOB_STATUS is never written. This was seen in production, where
a backfill left 2018–2025 unrebuilt.

## What Changes

- The processor reads the exact manifest version named in the triggering S3 event (body and
  metadata), so `reprocess_all`, `reprocess_seasons`, `correlation_id` and the trace context belong
  to the write that invoked it.
- The "previous manifest" used by the normal-refresh season diff is the version immediately before
  the triggering one, not the second-newest version in the bucket.
- An event without a `versionId` (unversioned bucket) keeps today's behavior: latest object,
  second-newest as previous.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/data-processing-pipeline`: "Select seasons to process" is decided from the manifest
  version that triggered the run, so a concurrent manifest write can't change which seasons a run
  rebuilds.

## Impact

- **Code:** `src/processor/handler.py` (`_lambda_handler_impl`, `get_previous_version_id`).
- **IAM:** none. Reading by version uses `s3:GetObjectVersion`, which the processor role already
  has on the raw prefix, and `s3:ListBucketVersions` is already used today.
- **Ops:** re-run the Yahoo backfill once this is deployed.
