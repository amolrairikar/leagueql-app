## Decisions

- **Idle rule, not onboard-to-access gap.** Eligibility is measured from the latest activity to
  now, so a long-lived league that is still opened is never removed.
- **Dry run by default.** Only `LEAGUE_REAPER_DRY_RUN=false` enables deletion.
- **No per-run cap.** A removed league can be connected again. A remaining-time floor stops the
  run cleanly so no deletion is cut off mid-way.
- **Retry safety.** GSI3 membership comes from `METADATA`, so the reaper deletes raw S3 data
  first and the shared deletion removes `METADATA` last. A partial failure stays discoverable.
- **Stale index reads.** Each candidate is re-read with a consistent read before deletion, and
  credential cleanup excludes every league already removed in the run.
- **Replication.** Only the primary region is written: S3 delete markers and DynamoDB global
  table deletes replicate, and the bucket lifecycle expires old versions after 2 days.

## Risks

- A never-recorded league onboarded before access tracking shipped (2026-06-10) can be removed
  after less than a full year of observed inactivity. Accepted.
- Delete permissions are first exercised by the first real deletion; the error alarm covers it.
