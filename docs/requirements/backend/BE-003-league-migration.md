# BE-003: League Migration

## Description
Migrates an onboarded league from one platform to another (e.g. ESPN → Sleeper) while
preserving all-time history under a single canonical league ID. Triggered by
`POST /leagues/{leagueId}/migrate`. The API writes a `LEAGUE_LOOKUP` entry for the new
platform league ID, records the manager identity mapping in a `PLATFORM_MIGRATION` item,
updates `METADATA` to reflect the new active platform, then invokes the onboarder for the
destination platform's data. The onboarder reads the manager mapping to resolve
cross-platform owner IDs so metrics remain continuous.

## Scope
- Endpoint: `POST /leagues/{leagueId}/migrate` (`src/api/routes.py::migrate_league`).
- Request body: `MigrateRequest` (`newPlatformLeagueId`, `newPlatform`, `managerMapping`,
  plus `season`/`s2`/`swid` when destination is ESPN).
- DynamoDB items: `LEAGUE_LOOKUP`, `PLATFORM_MIGRATION#{from}#{to}`, updated `METADATA`.

## Edge Cases
- **Operation already in progress:** if `METADATA` shows an active job, return `409`.
- **Destination league already onboarded:** if the new platform league ID resolves to an
  existing canonical league, return `409` "New platform league is already onboarded."
- **Source league not found:** return `404`.
- **Manager left the league:** mapping entries may use `newPlatformOwnerId =
  "__not_returning__"` to mark managers with no destination-platform identity.
- **ESPN destination:** requires `season`, `s2`, `swid`.
- **Partial migration setup failure:** DynamoDB write failures before invoking the
  onboarder return `500` "Failed to set up migration."
- **Onboarder invoke failure:** return `500` "Failed to trigger migration" (metadata may
  already be partially written — must be retry-safe).

## Acceptance Criteria
- [ ] `POST /leagues/{leagueId}/migrate` returns `202` with `{ data: { correlation_id } }`.
- [ ] A `LEAGUE_LOOKUP` item for `newPlatformLeagueId#newPlatform` pointing at the existing
      canonical league ID is written.
- [ ] A `PLATFORM_MIGRATION#{from}#{to}` item stores the full manager mapping.
- [ ] `METADATA` is updated with `active_platform`, `migrated_from`, `migrated_at`, and the
      active job ID.
- [ ] Migrating to an already-onboarded destination, or while an operation is in progress,
      returns `409`.
- [ ] After processing, all-time metrics span both platforms under one canonical league ID.

## Sources
`src/api/routes.py`, `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md` (PLATFORM_MIGRATION).
