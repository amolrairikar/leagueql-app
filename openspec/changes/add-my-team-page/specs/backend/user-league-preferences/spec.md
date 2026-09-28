# Spec Delta

## Purpose

Stores each signed-in user's personal preferences for a league. Today that is the team they
claim as their own. The frontend reads it through `GET`/`PUT /leagues/{leagueId}/me` to
personalize the My Team page.

## ADDED Requirements

### Requirement: Read the caller's league preferences
`GET /leagues/{leagueId}/me?platform=` SHALL return the authenticated caller's preferences for
that league as `{"owner_id": <string | null>}` in the standard response envelope's `data`. `owner_id` SHALL be `null` when the caller has
not claimed a team. The response SHALL NOT include any other user's preferences.

#### Scenario: No claim yet
- **WHEN** an authenticated caller who has never claimed a team requests `GET /leagues/{leagueId}/me`
- **THEN** the API returns `200` with `data` = `{"owner_id": null}`

#### Scenario: Existing claim
- **WHEN** an authenticated caller who previously claimed owner `U1` requests `GET /leagues/{leagueId}/me`
- **THEN** the API returns `200` with `data` = `{"owner_id": "U1"}`

#### Scenario: Claims are per user
- **WHEN** user A has claimed owner `U1` and user B, who has not claimed a team, requests `GET /leagues/{leagueId}/me` for the same league
- **THEN** user B receives `{"owner_id": null}`

### Requirement: Save the caller's claimed team
`PUT /leagues/{leagueId}/me?platform=` with body `{"owner_id": "<id>"}` SHALL save that owner as
the caller's claimed team for the league, replacing any earlier claim, and SHALL return the saved
preferences. The `owner_id` SHALL be an owner that appears as a team's primary owner in the
league's stored teams. Otherwise the API SHALL return `400` and SHALL NOT change the stored
claim.

#### Scenario: Claim a team
- **WHEN** an authenticated caller sends `PUT /leagues/{leagueId}/me` with an `owner_id` that is a primary owner in the league's teams
- **THEN** the API returns `200` with the saved `owner_id`, and a later `GET` returns the same value

#### Scenario: Change the claim
- **WHEN** a caller who claimed owner `U1` sends `PUT` with owner `U2`, a valid owner in the league
- **THEN** the stored claim becomes `U2`

#### Scenario: Unknown owner rejected
- **WHEN** a caller sends `PUT /leagues/{leagueId}/me` with an `owner_id` that is not a primary owner of any team in the league
- **THEN** the API returns `400` and the caller's stored claim is unchanged

### Requirement: Authentication and league access for preferences
Both preference endpoints SHALL require an authenticated caller and SHALL return `401` without
one. They SHALL return `404` when the league is not onboarded. They SHALL apply the same
membership gate as league reads: for ESPN and Yahoo leagues, only the owner or a member may read
or write preferences, and anyone else gets `403`. For Sleeper leagues, any authenticated caller
may.

#### Scenario: Unauthenticated
- **WHEN** a request to `GET` or `PUT /leagues/{leagueId}/me` carries no authenticated user
- **THEN** the API returns `401`

#### Scenario: Unknown league
- **WHEN** an authenticated caller requests preferences for a league that is not onboarded
- **THEN** the API returns `404`

#### Scenario: Non-member of a gated league
- **WHEN** an authenticated caller who is neither the owner nor a member of an ESPN or Yahoo league requests `GET` or `PUT /leagues/{leagueId}/me`
- **THEN** the API returns `403` and nothing is stored

#### Scenario: Sleeper league open to any signed-in user
- **WHEN** any authenticated caller requests `GET /leagues/{leagueId}/me` for a Sleeper league
- **THEN** the API returns `200`

### Requirement: Preferences are deleted with the league
A user's preferences for a league SHALL be removed when that league is deleted.

#### Scenario: League deletion removes claims
- **WHEN** a league with one or more users' claimed teams is deleted
- **THEN** no preference records for that league remain
