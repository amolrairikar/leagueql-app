# user-leagues Specification

## Purpose
Lets a signed-in user list every league they own, have joined through an invite, or have opened
on Sleeper. It maintains a per-user league membership index and serves it from `GET /me/leagues`.

## Requirements

### Requirement: Index the onboarding owner
When a user-initiated onboard first creates a league's METADATA, the system SHALL record the owner in the league's membership index atomically with that METADATA write. System-initiated onboards (no owner) SHALL record no one.

#### Scenario: Owner onboards a league
- **WHEN** a signed-in user onboards a new league
- **THEN** the league appears in that user's `GET /me/leagues` response

#### Scenario: System onboard
- **WHEN** a league is onboarded without an owner
- **THEN** no membership index entry is created for it

#### Scenario: Refresh or migrate leaves the index unchanged
- **WHEN** an existing league is refreshed or migrated to another platform
- **THEN** its membership index entries are preserved and still list the league for each indexed user

### Requirement: Index invited members
When a caller successfully redeems an invite token, the system SHALL record them in that league's membership index. Redeeming again SHALL be idempotent and SHALL NOT change the recorded join time.

#### Scenario: Invite redeemed
- **WHEN** a caller redeems a valid invite token for an ESPN or Yahoo league
- **THEN** the league appears in that caller's `GET /me/leagues` response

#### Scenario: Redeemed twice
- **WHEN** the same caller redeems an invite for the same league again
- **THEN** exactly one entry exists for that caller and league, with its original join time

### Requirement: Index the new owner on ownership transfer
When a caller successfully claims ownership of a league, the system SHALL record them in that league's membership index. The previous owner SHALL keep their entry, because they remain a member.

#### Scenario: Ownership claimed
- **WHEN** a caller successfully claims ownership of a league
- **THEN** the league appears in both the new owner's and the previous owner's `GET /me/leagues` responses

### Requirement: Index Sleeper league opens
When an authenticated caller successfully opens a Sleeper league via `GET /leagues/{leagueId}`, the system SHALL record them in that league's membership index. This SHALL be best-effort: an existing entry is left unchanged, and a failure to write never changes the endpoint's response. ESPN and Yahoo opens SHALL NOT write entries.

#### Scenario: First Sleeper open
- **WHEN** a signed-in user opens a Sleeper league they have no entry for
- **THEN** the league appears in their `GET /me/leagues` response

#### Scenario: Index write fails
- **WHEN** recording the Sleeper open fails with a storage error
- **THEN** `GET /leagues/{leagueId}` still returns its normal `200` response

#### Scenario: ESPN open writes nothing
- **WHEN** a member opens an ESPN or Yahoo league
- **THEN** no membership index entry is written by the open

### Requirement: Remove index entries with the league
Deleting a league SHALL remove all of its membership index entries.

#### Scenario: League deleted
- **WHEN** the owner deletes a league
- **THEN** the league no longer appears in any user's `GET /me/leagues` response

### Requirement: List the caller's leagues
`GET /me/leagues` SHALL require authentication. It SHALL return `200` with `Cache-Control: no-store` and a list of the caller's indexed leagues, sorted by `updated_at` descending. An unauthenticated request SHALL return `401`.

#### Scenario: Caller has leagues
- **WHEN** an authenticated caller with indexed leagues calls `GET /me/leagues`
- **THEN** the API returns `200` with one entry per league, most recently updated first

#### Scenario: Caller has no leagues
- **WHEN** an authenticated caller with no indexed leagues calls `GET /me/leagues`
- **THEN** the API returns `200` with an empty list

#### Scenario: Unauthenticated
- **WHEN** `GET /me/leagues` is called without a valid session
- **THEN** the API returns `401`

### Requirement: League list entry contents
Each entry SHALL include `league_id` and `platform` for the league's current platform, `league_name` (nullable), `seasons` (unified across platforms, ascending), `updated_at` (`last_refresh_at`, else `onboarded_at`), `migrated_from` (nullable), and `espn_reauth_required`.

#### Scenario: Migrated league
- **WHEN** an indexed league was migrated from ESPN to Sleeper
- **THEN** its entry has `platform` `SLEEPER`, a Sleeper `league_id` that opens it, `migrated_from` `ESPN`, and `seasons` spanning both platforms

#### Scenario: Sleeper league across renewals
- **WHEN** an indexed Sleeper league has a different league ID for each season
- **THEN** its entry's `league_id` is the one for its latest onboarded season, and a pending (not yet started) season is not included

#### Scenario: Never refreshed
- **WHEN** an indexed league has no `last_refresh_at`
- **THEN** its `updated_at` equals its `onboarded_at`

### Requirement: Re-auth flag only for the owner
`espn_reauth_required` SHALL be true only when the caller owns the league, the league's current platform is ESPN, it is enrolled in auto-refresh, and the caller's stored ESPN credentials need re-entry. In every other case it SHALL be false.

#### Scenario: Owner needs to reconnect
- **WHEN** the caller owns an auto-refreshed ESPN league whose stored credentials were rejected
- **THEN** that entry has `espn_reauth_required` true

#### Scenario: Member never sees the flag
- **WHEN** a non-owner member lists the same league
- **THEN** that entry has `espn_reauth_required` false

### Requirement: Skip stale index entries
An index entry whose league no longer has METADATA or any onboarded season SHALL be omitted from the response, and SHALL NOT cause an error.

#### Scenario: Orphaned entry
- **WHEN** an index entry points to a league whose METADATA is missing
- **THEN** that league is left out and the remaining leagues are returned with `200`

### Requirement: Backfill existing memberships
A one-off backfill SHALL create index entries for every existing league's owner and members, so they appear without further action. It SHALL be idempotent. Sleeper leagues opened before the feature can't be recovered, so they appear after the user next opens them.

#### Scenario: Existing ESPN member
- **WHEN** the backfill runs for a league whose METADATA lists a user in `members`
- **THEN** that league appears in the user's `GET /me/leagues` response

#### Scenario: Re-run
- **WHEN** the backfill runs a second time
- **THEN** no duplicate entries are created and existing join times are unchanged
