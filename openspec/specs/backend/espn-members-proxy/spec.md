# espn-members-proxy Specification

## Purpose
Server-side proxy to the ESPN Fantasy API that returns the list of members (owners) for a given ESPN league. `POST /leagues/{leagueId}/espn_members` makes the request from the Lambda using the caller's `swid`/`s2` cookies, avoiding browser CORS restrictions. Primarily used by the migration flow to build the manager identity mapping between platforms.

## Requirements

### Requirement: Return ESPN league members
The API SHALL return the ESPN league's members for a valid league and credentials, falling back to the owner ID when a display name is absent.

#### Scenario: Valid request
- **WHEN** `POST /leagues/{leagueId}/espn_members` is called with a valid ESPN league and credentials
- **THEN** the API returns `200` with `data: [{ owner_id, display_name }]`

#### Scenario: Member without display name
- **WHEN** a returned member has no `displayName`
- **THEN** its `display_name` falls back to the member `id`

### Requirement: Validate upstream URL inputs
The API SHALL constrain `espnLeagueId` to digits (`^\d+$`) and `season` to a 4-digit year (`^\d{4}$`), returning `422` before any upstream request.

#### Scenario: Non-numeric identifiers rejected
- **WHEN** `espnLeagueId` is non-numeric or `season` is not a 4-digit year
- **THEN** the API returns `422` and makes no upstream ESPN request

### Requirement: Handle upstream failures
The API SHALL return `502` on ESPN HTTP, network, or parse failures, and `404` when the current league is not onboarded, using a bounded 10s timeout.

#### Scenario: ESPN HTTP error
- **WHEN** ESPN returns an HTTP error (bad credentials / not found)
- **THEN** the API returns `502` "Failed to fetch ESPN league members"

#### Scenario: ESPN unreachable
- **WHEN** the ESPN API is unreachable
- **THEN** the API returns `502` "Failed to reach ESPN API"

#### Scenario: Unparseable response
- **WHEN** the ESPN response cannot be parsed
- **THEN** the API returns `502` "Failed to parse ESPN API response"

#### Scenario: Current league not onboarded
- **WHEN** `lookup_league` misses for the current league
- **THEN** the API returns `404`

### Requirement: Protect credentials
The API SHALL use `swid`/`s2` only for the proxied request and never log or persist them.

#### Scenario: Credentials not persisted
- **WHEN** the proxy makes the ESPN request
- **THEN** the `swid`/`s2` values appear in no log line and no stored item

### Requirement: Owner-gated proxy
The API SHALL restrict the members proxy to the league owner.

#### Scenario: Non-owner proxy call
- **WHEN** a non-owner calls the ESPN-members proxy
- **THEN** the API returns `403`
