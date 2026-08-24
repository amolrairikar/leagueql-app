# league-migration Specification

## Purpose
Migrate an onboarded league from one platform to another (e.g. ESPN → Sleeper) while preserving all-time history under a single canonical league ID. `POST /leagues/{leagueId}/migrate` writes a `LEAGUE_LOOKUP` for the new platform league ID, records the manager identity mapping in a `PLATFORM_MIGRATION` item, updates `METADATA` to the new active platform, then invokes the onboarder for the destination platform. The onboarder reads the mapping to resolve cross-platform owner IDs so metrics stay continuous.

## Requirements

### Requirement: Migrate a league to a new platform
The API SHALL accept a migration request, write the migration records, and invoke the destination-platform onboarder, returning `202`.

#### Scenario: Valid migration
- **WHEN** `POST /leagues/{leagueId}/migrate` is called for an onboarded source league
- **THEN** the API returns `202` with `{ data: { correlation_id } }`, writes a `LEAGUE_LOOKUP` for `newPlatformLeagueId#newPlatform` pointing at the existing canonical league ID, writes a `PLATFORM_MIGRATION#{from}#{to}` item with the full manager mapping, and updates `METADATA` with `active_platform`, `migrated_from`, `migrated_at`, and the active job ID

#### Scenario: ESPN destination requirements
- **WHEN** the destination platform is ESPN
- **THEN** the request requires `season`, `s2`, and `swid`

#### Scenario: Continuous cross-platform metrics
- **WHEN** the destination data has been processed
- **THEN** all-time metrics span both platforms under one canonical league ID

### Requirement: Reject invalid migration targets
The API SHALL reject migrating to an already-onboarded destination or while an operation is in progress, and SHALL return `404` for a missing source league.

#### Scenario: Destination already onboarded
- **WHEN** the new platform league ID resolves to an existing canonical league
- **THEN** the API returns `409` "New platform league is already onboarded."

#### Scenario: Operation in progress
- **WHEN** `METADATA` shows an active job
- **THEN** the API returns `409`

#### Scenario: Source league not found
- **WHEN** the source league is not onboarded
- **THEN** the API returns `404`

### Requirement: Validate the manager mapping
The API SHALL strictly validate `managerMapping` entries and reject malformed input with `422` before any DynamoDB write, supporting a `__not_returning__` sentinel for managers with no destination identity.

#### Scenario: Malformed mapping entry
- **WHEN** a `managerMapping` entry has unknown keys, non-string field values, or the list exceeds the size limits
- **THEN** the API returns `422` and writes no `PLATFORM_MIGRATION` item

#### Scenario: Manager not returning
- **WHEN** a mapping entry marks a manager with `newPlatformOwnerId = "__not_returning__"`
- **THEN** that manager is recorded as having no destination-platform identity

### Requirement: Report migration setup failures
The API SHALL return `500` on setup or invoke failures in a retry-safe way.

#### Scenario: DynamoDB setup failure
- **WHEN** a DynamoDB write fails before invoking the onboarder
- **THEN** the API returns `500` "Failed to set up migration."

#### Scenario: Onboarder invoke failure
- **WHEN** the onboarder invocation fails after metadata was partially written
- **THEN** the API returns `500` "Failed to trigger migration" and the operation remains retry-safe

### Requirement: Owner-gated migration
The API SHALL restrict migration to the league owner.

#### Scenario: Non-owner migration
- **WHEN** a non-owner calls migrate
- **THEN** the API returns `403`
