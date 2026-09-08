## MODIFIED Requirements

### Requirement: Migrate a league to a new platform
The API SHALL accept a migration request, write the migration records, and invoke the destination-platform onboarder, returning `202`. The API SHALL NOT write the destination `LEAGUE_LOOKUP`; that record is written by the onboarder only after it successfully fetches the destination-platform league, so a failed or unauthorized migration leaves no destination mapping behind.

#### Scenario: Valid migration
- **WHEN** `POST /leagues/{leagueId}/migrate` is called for an onboarded source league
- **THEN** the API returns `202` with `{ data: { correlation_id } }`, writes a `PLATFORM_MIGRATION#{from}#{to}` item with the full manager mapping, updates `METADATA` with `active_platform`, `migrated_from`, `migrated_at`, and the active job ID, and invokes the onboarder — **without** writing a `LEAGUE_LOOKUP` for `newPlatformLeagueId#newPlatform`

#### Scenario: Destination lookup written after successful fetch
- **WHEN** the onboarder successfully fetches the destination-platform league
- **THEN** it writes the `LEAGUE_LOOKUP` for `newPlatformLeagueId#newPlatform` pointing at the existing canonical league ID, using a conditional put that does not overwrite an existing destination mapping

#### Scenario: ESPN destination requirements
- **WHEN** the destination platform is ESPN
- **THEN** the request requires `season`, `s2`, and `swid`

#### Scenario: Continuous cross-platform metrics
- **WHEN** the destination data has been processed
- **THEN** all-time metrics span both platforms under one canonical league ID

## ADDED Requirements

### Requirement: Rollback-safe destination binding
The migration flow SHALL NOT create a durable `LEAGUE_LOOKUP` for a destination league it cannot access, so a caller cannot squat on or deny onboarding of a destination-platform league ID they do not control.

#### Scenario: Failed destination fetch leaves no mapping
- **WHEN** the onboarder cannot fetch the destination-platform league (e.g. missing or invalid ESPN credentials)
- **THEN** no `LEAGUE_LOOKUP` for `newPlatformLeagueId#newPlatform` is persisted, the job is recorded `FAILED`, and the destination league ID remains onboardable by its legitimate owner

#### Scenario: Concurrent destination claim
- **WHEN** two operations race to write the same destination `LEAGUE_LOOKUP`
- **THEN** the conditional put ensures only the first succeeds and the second does not overwrite the existing mapping
