## MODIFIED Requirements

### Requirement: Backfill existing leagues idempotently
The backfill script SHALL re-onboard every Sleeper league with `reprocess_all` (via REFRESH, preserving METADATA), rebuilding transactions for all seasons, and SHALL be idempotent. When run with `--refetch-all`, it SHALL also request `refetchAll=true` so every season is re-fetched from the platform instead of only reprocessed from S3.

#### Scenario: Backfill run
- **WHEN** the backfill script runs with `--execute`
- **THEN** it invokes the onboarder in `REFRESH` mode with `reprocess_all=True` for each Sleeper league (preserving owner/members), rebuilding transactions for all seasons from S3, and running it twice produces the same result

#### Scenario: Backfill run with refetch-all
- **WHEN** the backfill script runs with `--execute --refetch-all`
- **THEN** each onboarder invocation is a `REFRESH` with `reprocessAll=true` and `refetchAll=true`, so every season's raw data is re-fetched from the platform before all views are rebuilt
