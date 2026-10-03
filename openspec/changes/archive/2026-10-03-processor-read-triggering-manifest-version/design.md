# Design

## Context

`_lambda_handler_impl` calls `s3_client.get_object(Bucket, Key)` and
`get_previous_version_id(bucket, key)`, which returns the second-newest version from
`list_object_versions`. Two writers update the same manifest: the onboarder (`put_object` with
`correlation_id` and maybe `reprocess_all`) and the lineup backfill (`copy_object` with
`MetadataDirective=REPLACE`, `{"reprocess_seasons": season}`). The bucket is versioned, and every
`ObjectCreated` event carries `s3.object.versionId`.

## Goals / Non-Goals

**Goals:** a run's behavior depends only on the version that triggered it.

**Non-Goals:** serializing processor runs, or changing the lineup backfill's metadata. Its runs
already behave correctly once each run reads its own version.

## Decisions

### D1. Read the triggering version
Use `record["s3"]["object"].get("versionId")` and `get_object(..., VersionId=...)`. The event's
`versionId` is the exact object whose creation invoked the Lambda.
*Alternative:* have the lineup backfill copy across `reprocess_all`/`correlation_id`. Rejected:
that only narrows the race, mixes two jobs' metadata, and still leaves the wrong previous version.

### D2. Previous version relative to the triggering one
`get_previous_version_id(bucket, key, version_id=None)` sorts versions newest-first. With a
`version_id`, it returns the entry immediately after it (older). If the version is missing or is
the oldest, it returns `None`, which the caller already treats as "no previous manifest" (process
every season). Without a `version_id`, it keeps returning the second-newest.
`list_object_versions` is paginated, but the processor reads one key that gets only a handful of
writes per refresh, so one page (up to 1000 versions) is enough. An older triggering version
missing from the page falls back to `None` (full rebuild), which is safe.

## Risks / Trade-offs

- **[Risk]** A version listed past the first page is treated as having no previous version.
  → It rebuilds every season: correct, just more work, and very unlikely.
- **[Trade-off]** Two concurrent runs can still both write views, but each now writes the seasons
  its own trigger asked for, so the results agree.
