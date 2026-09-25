# league-export Specification

## Purpose

Let a league member take a league's processed data out of LeagueQL by serving a bundle of the
precomputed views for a caller-selected set of seasons in a single request.

## Requirements

### Requirement: Export processed views for selected seasons
The API SHALL expose `GET /leagues/{leagueId}/export` that, given a `platform` and a `seasons`
query parameter (a comma-separated list of season years), resolves the platform league id to its
canonical league id and returns the processed views for each requested season. The response body
SHALL be `{ "data": { "<season>": { "<view>": [ ...rows ] } } }`, where each view key is the
lowercased view name (`standings`, `weekly_standings`, `matchups`, `draft`, `transactions`,
`playoff_bracket`, `league_settings`, `teams`). A view that has no stored data for a season SHALL
be omitted from that season's object rather than returned as an empty list.

#### Scenario: Bundle returned for requested seasons
- **WHEN** a member requests `GET /leagues/{leagueId}/export?platform=SLEEPER&seasons=2023,2024`
  for an onboarded league
- **THEN** the response is `200` with a `data` object keyed by `"2023"` and `"2024"`, each
  containing the league's available processed views for that season

#### Scenario: Empty or absent views omitted
- **WHEN** a requested season has no data stored for a given view
- **THEN** that view key is absent from the season's object in the response

### Requirement: Concatenate chunked and multi-item views in the export
The export SHALL assemble each view's rows the same way the query endpoint does: single-item views
(`standings`, `weekly_standings`, `draft`, `playoff_bracket`, `league_settings`) are read as one
item, while `matchups` (stored per week) and `transactions` (stored in chunks) are read via a
season-scoped prefix scan whose items' `data` lists are concatenated in sort-key order across all
pages. The `teams` view (stored once across all seasons) SHALL be included per requested season,
filtered to that season's rows.

#### Scenario: Transactions chunks concatenated
- **WHEN** a season's transactions are stored across multiple chunk items
- **THEN** the season's `transactions` value in the export contains every chunk's rows concatenated
  in sort-key order

#### Scenario: Teams filtered per season
- **WHEN** the export is built for a requested season
- **THEN** the season's `teams` value contains only the team rows whose `season` equals that season

### Requirement: Member-gated export
The export SHALL apply the same league-membership authorization as the query endpoint: ESPN and
Yahoo leagues SHALL be restricted to the league owner and invited members, returning `403` for a
non-member; Sleeper leagues SHALL remain open.

#### Scenario: Non-member ESPN export forbidden
- **WHEN** a caller who is not the owner or a member requests the export for an ESPN league
- **THEN** the API returns `403`

#### Scenario: Sleeper export open
- **WHEN** any authenticated caller requests the export for an onboarded Sleeper league
- **THEN** the API does not reject the request on membership grounds

### Requirement: Validate export request and existence
The export SHALL return `400` when the `seasons` parameter is missing, empty, or contains no valid
season, and SHALL return `404` when the league is not onboarded or has no data for any requested
season. Requested seasons that the league does not have SHALL NOT cause a `500`.

#### Scenario: Missing seasons parameter
- **WHEN** the export is requested without a usable `seasons` value
- **THEN** the API returns `400`

#### Scenario: Un-onboarded league
- **WHEN** the export is requested for a league that has not been onboarded
- **THEN** the API returns `404`

### Requirement: Serialize numbers and cache the export response
The export SHALL convert DynamoDB `Decimal` values to JSON numbers before serializing, and SHALL
set `Cache-Control: private, max-age=300` on a successful response.

#### Scenario: Decimals converted and cache header set
- **WHEN** an export request succeeds
- **THEN** numeric values are returned as JSON numbers and the response sets
  `Cache-Control: private, max-age=300`
