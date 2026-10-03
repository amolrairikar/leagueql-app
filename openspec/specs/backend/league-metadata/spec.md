# league-metadata Specification

## Purpose
Return whether a league has been onboarded and, if so, its display name and onboarded seasons. `GET /leagues/{leagueId}` resolves the platform league ID to a canonical league ID, reads the `METADATA` item, and lists seasons. The frontend uses it to decide whether a league is onboarded and to populate season selectors.

## Requirements

### Requirement: Return league metadata
The API SHALL return the onboarded seasons and league name with `200` for an onboarded league, and `404` for an un-onboarded one. The `200` payload SHALL additionally include `onboarded_at` (ISO 8601) and `last_refresh_at` (ISO 8601, nullable — absent until the league's first successful refresh), so the frontend can determine when the league's data was last updated.

#### Scenario: Onboarded league
- **WHEN** `GET /leagues/{leagueId}` is called for an onboarded league
- **THEN** the API returns `200` with `{ seasons, league_name, is_owner, last_refresh_at, onboarded_at }`

#### Scenario: Never-refreshed league
- **WHEN** an onboarded league has never been refreshed (no `last_refresh_at` on `METADATA`)
- **THEN** the API returns `200` with `last_refresh_at` null and `onboarded_at` set

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

### Requirement: Report lineup data status
The league metadata response SHALL include `pending_lineup_seasons` and `failed_lineup_seasons`:
ascending-sorted season lists for seasons whose weekly lineups are still being backfilled or could
not be backfilled yet (`backend/yahoo-lineup-backfill`). Each list SHALL be empty when the league
has no such seasons.

#### Scenario: Seasons pending
- **WHEN** `GET /leagues/{leagueId}` is called for a Yahoo league whose 2024 and 2025 lineups are
  still being backfilled
- **THEN** the response includes `pending_lineup_seasons: ["2024", "2025"]` and
  `failed_lineup_seasons: []`

#### Scenario: Season failed
- **WHEN** a league's 2019 lineup backfill exhausted its retries
- **THEN** the response includes `"2019"` in `failed_lineup_seasons`

#### Scenario: No lineup status recorded
- **WHEN** the league's metadata has no lineup status (any ESPN or Sleeper league, or a fully
  backfilled Yahoo league)
- **THEN** both lists are returned empty

### Requirement: Report ESPN re-authentication required

The league metadata response SHALL include `espn_reauth_required` (boolean) and
`espn_credentials_failed_at` (ISO 8601, nullable). `espn_reauth_required` SHALL be true only when
the caller is the league owner, the league is an ESPN league with `auto_refresh_enabled`, and the
owner's `ESPN_CREDENTIALS` item is missing or carries `auth_failed_at`.
`espn_credentials_failed_at` SHALL carry that `auth_failed_at` when present. Both SHALL be
false/null for every other caller or league.

#### Scenario: Owner with rejected cookies

- **WHEN** the owner reads an auto-refresh-enabled ESPN league and their stored credentials carry
  `auth_failed_at`
- **THEN** the response has `espn_reauth_required` true and `espn_credentials_failed_at` set to that
  timestamp

#### Scenario: Owner with missing cookies

- **WHEN** the owner reads an auto-refresh-enabled ESPN league and has no stored credentials
- **THEN** the response has `espn_reauth_required` true and `espn_credentials_failed_at` null

#### Scenario: Healthy cookies or not enrolled

- **WHEN** the owner's stored credentials carry no `auth_failed_at`, or the league is not enrolled
  in auto-refresh, or the league is not an ESPN league
- **THEN** the response has `espn_reauth_required` false

#### Scenario: Non-owner

- **WHEN** a member who is not the owner reads the league
- **THEN** the response has `espn_reauth_required` false and `espn_credentials_failed_at` null
