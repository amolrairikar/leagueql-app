# league-access-tracking Specification

## Purpose
Record when a league was last opened so stale leagues — ones nobody has viewed in a long time — can later be identified for pruning/archival. When a member opens a league via `GET /leagues/{leagueId}`, the endpoint records a `last_accessed_at` ISO-8601 (UTC) timestamp on the league's `METADATA` item, throttled to at most once per hour per league. The field is internal (never returned in any API response).

## Requirements

### Requirement: Record last-accessed timestamp
Opening an onboarded league SHALL write `last_accessed_at` on `METADATA` when the timestamp is absent or stale.

#### Scenario: Timestamp absent
- **WHEN** an onboarded league is opened and `last_accessed_at` is absent (older items / never opened)
- **THEN** the current timestamp is written

#### Scenario: Stale timestamp
- **WHEN** `last_accessed_at` is older than an hour (or malformed/unparseable)
- **THEN** a fresh timestamp is written

### Requirement: Throttle writes to once per hour
The write SHALL be skipped when `last_accessed_at` is within the throttle window, evaluated in memory against the already-fetched `METADATA`.

#### Scenario: Fresh timestamp
- **WHEN** a league whose `last_accessed_at` is within the last hour is opened again
- **THEN** no `update_item` call is made (the throttle holds)

### Requirement: Tracking never breaks the read
A failure of the tracking write SHALL NOT change the endpoint response, and the write SHALL be conditional on the item still existing.

#### Scenario: Write fails
- **WHEN** the tracking `update_item` raises a DynamoDB error or a conditional-check failure (e.g. concurrent delete)
- **THEN** the error is swallowed and `GET /leagues/{leagueId}` still returns `200` (no resurrection of a deleted item)

### Requirement: Access recorded only after the membership gate
Access SHALL be recorded only after `require_league_member` passes, and `last_accessed_at` SHALL never appear in an API response.

#### Scenario: Non-member does not record
- **WHEN** a non-member is `403`'d on an ESPN league
- **THEN** no `last_accessed_at` is written

#### Scenario: Field stays internal
- **WHEN** any league endpoint responds
- **THEN** `last_accessed_at` is not included and the OpenAPI spec is unchanged
