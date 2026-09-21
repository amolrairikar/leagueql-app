# yahoo-members-proxy Specification

## Purpose
Server-side proxy to the Yahoo Fantasy API that returns the managers (members) of a Yahoo league for the migration mapping exercise, using the caller's linked user-level Yahoo OAuth token. `POST /leagues/{leagueId}/yahoo_members` resolves the entered destination Yahoo numeric league id to its `league_key` and fetches that league's teams/managers server-side (the token never reaches the browser). Mirrors `backend/espn-members-proxy`.

## Requirements

### Requirement: Return Yahoo league members
The API SHALL return the destination Yahoo league's managers for a caller with a valid linked Yahoo token, falling back to the Yahoo owner id when a nickname is absent. `{leagueId}` is the numeric source league; the destination Yahoo league id is the `yahooLeagueId` query parameter.

#### Scenario: Valid request
- **WHEN** `POST /leagues/{leagueId}/yahoo_members?yahooLeagueId={id}` is called by the source league owner who has a valid linked Yahoo token and is a member of the destination Yahoo league
- **THEN** the API returns `200` with `data: [{ owner_id, display_name }]`, where `owner_id` is the manager's Yahoo `guid`

#### Scenario: Manager without a nickname
- **WHEN** a returned manager has no `nickname`
- **THEN** its `display_name` falls back to the manager's `owner_id`

### Requirement: Require a linked Yahoo account
The API SHALL require a valid linked Yahoo token and SHALL return `403` when the caller has no valid link or the stored refresh token is revoked, so the frontend can route to the OAuth link.

#### Scenario: No valid link
- **WHEN** the caller has no valid `YAHOO_OAUTH` item, or the stored refresh token yields a Yahoo `invalid_grant`
- **THEN** the API returns `403` and makes no members request

### Requirement: Owner-gated proxy
The API SHALL restrict the members proxy to the source league's owner.

#### Scenario: Non-owner proxy call
- **WHEN** a non-owner calls the Yahoo-members proxy
- **THEN** the API returns `403`

### Requirement: Validate inputs
The API SHALL constrain `yahooLeagueId` to digits (`^\d+$`), returning `422` before any upstream request.

#### Scenario: Non-numeric league id rejected
- **WHEN** `yahooLeagueId` is non-numeric
- **THEN** the API returns `422` and makes no upstream Yahoo request

### Requirement: Handle upstream and lookup failures
The API SHALL return `404` when the entered Yahoo league is not among the caller's Yahoo leagues, `502` on Yahoo HTTP, network, or parse failures, and `404` when the source league is not onboarded.

#### Scenario: League not in the caller's account
- **WHEN** the entered `yahooLeagueId` is not among the linked caller's NFL leagues
- **THEN** the API returns `404` distinct from a `502`, indicating the league isn't in the caller's Yahoo account

#### Scenario: Yahoo upstream failure
- **WHEN** the Yahoo API returns an HTTP error, is unreachable, or its response cannot be parsed
- **THEN** the API returns `502`

#### Scenario: Source league not onboarded
- **WHEN** `lookup_league` misses for the source league
- **THEN** the API returns `404`

### Requirement: Protect tokens
The API SHALL use the caller's Yahoo access token only for the proxied request and SHALL never log or return it.

#### Scenario: Token not disclosed
- **WHEN** the proxy makes the Yahoo request
- **THEN** the Yahoo access token appears in no log line, trace, API response, or stored item
