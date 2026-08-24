# league-metadata Specification

## Purpose
Return whether a league has been onboarded and, if so, its display name and onboarded seasons. `GET /leagues/{leagueId}` resolves the platform league ID to a canonical league ID, reads the `METADATA` item, and lists seasons. The frontend uses it to decide whether a league is onboarded and to populate season selectors.

## Requirements

### Requirement: Return league metadata
The API SHALL return the onboarded seasons and league name with `200` for an onboarded league, and `404` for an un-onboarded one.

#### Scenario: Onboarded league
- **WHEN** `GET /leagues/{leagueId}` is called for an onboarded league
- **THEN** the API returns `200` with `{ seasons, league_name, is_owner }`

#### Scenario: Un-onboarded league
- **WHEN** the league is not in `LEAGUE_LOOKUP`
- **THEN** the API returns `404` with an onboarding hint

#### Scenario: Missing league name tolerated
- **WHEN** an older `METADATA` item has no `league_name`
- **THEN** the field may be null/omitted and the frontend tolerates it

### Requirement: Unified sorted seasons
The API SHALL return `seasons` as the unified, ascending-sorted list across all platforms for migrated leagues.

#### Scenario: Migrated league seasons
- **WHEN** a migrated league's metadata is read
- **THEN** `seasons` spans all platforms under one canonical league ID, sorted ascending

### Requirement: No-store caching
The API SHALL respond with `Cache-Control: no-store`.

#### Scenario: Cache header
- **WHEN** the metadata endpoint responds
- **THEN** it sets `Cache-Control: no-store`

### Requirement: Member-gated ESPN metadata with owner flag
The API SHALL include an `is_owner` flag and gate ESPN metadata reads to members; Sleeper reads stay open.

#### Scenario: Non-member ESPN read
- **WHEN** a non-member requests ESPN league metadata
- **THEN** the API returns `403` before any metadata is returned

#### Scenario: Owner flag returned
- **WHEN** metadata is returned
- **THEN** it includes `is_owner` so the frontend can gate owner-only actions

### Requirement: Record last access
On a successful open (after the membership gate) the API SHALL best-effort record a `last_accessed_at` timestamp on `METADATA`, throttled to once per hour, without affecting the response.

#### Scenario: Access timestamp recorded
- **WHEN** an onboarded league is successfully opened and it was last recorded over an hour ago
- **THEN** `last_accessed_at` is updated best-effort, and a failure to write it does not change the endpoint's response
