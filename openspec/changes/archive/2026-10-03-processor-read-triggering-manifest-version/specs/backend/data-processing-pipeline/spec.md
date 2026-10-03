# Spec Delta

## MODIFIED Requirements

### Requirement: Select seasons to process
The processor SHALL recompute only the latest season on a normal refresh, every season in the manifest when `reprocess_all=true`, and exactly the listed seasons when the manifest carries `reprocess_seasons`. These flags, the job's `correlation_id`, and the previous manifest used for the normal-refresh diff SHALL come from the manifest version that triggered the run, not from whichever version is newest when the run reads it.

#### Scenario: Normal refresh
- **WHEN** a normal refresh runs
- **THEN** only the latest season is recomputed (`resolve_seasons_to_process`)

#### Scenario: Reprocess all
- **WHEN** the manifest carries `reprocess_all=true`
- **THEN** the processor recomputes every season in the manifest from the raw season files already in S3

#### Scenario: Reprocess specific seasons
- **WHEN** the manifest carries `reprocess_seasons=2019`
- **THEN** the processor recomputes only season 2019 from the raw season files already in S3,
  regardless of the previous manifest's seasons

#### Scenario: Manifest overwritten before the run reads it
- **WHEN** a backfill writes the manifest with `reprocess_all=true` and, before the processor run it
  triggered reads the manifest, the lineup backfill copies it with `reprocess_seasons=2026`
- **THEN** the backfill's run still recomputes every season and records the backfill's
  `correlation_id`, and the lineup backfill's own run recomputes only 2026

#### Scenario: Previous manifest is relative to the triggering version
- **WHEN** a run is triggered by a manifest version that is no longer the newest
- **THEN** the previous manifest used for the season diff is the version written immediately before
  the triggering one

#### Scenario: Event without a version id
- **WHEN** the triggering S3 event carries no `versionId`
- **THEN** the processor reads the current manifest and uses the second-newest version as the
  previous manifest
