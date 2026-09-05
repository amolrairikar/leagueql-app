# query-precomputed-views Specification

## Purpose
Serve precomputed league views to the frontend. `GET /leagues/{leagueId}/query` resolves the platform league ID to its canonical league ID, maps `queryType` to a DynamoDB sort key, and returns the stored `data`. Season-scoped views require a season suffix (e.g. `STANDINGS#2024`); cross-season/collection views use a paginated prefix query that concatenates all matching items.

## Requirements

### Requirement: Query a suffixed view
The API SHALL return the matching `data` with `200` for a valid suffixed `queryType`. A suffixed view stored as a single item SHALL be served via an exact `get_item`. A suffixed view stored across multiple chunk items (the transactions view, `TRANSACTIONS#{season}#{chunk}`) SHALL be served via a fully paginated `begins_with` prefix query that concatenates the chunks' `data` in sort-key order into one flat list. The prefix SHALL match both the chunked items and any legacy single-key item written before chunking, so already-onboarded leagues continue to resolve without a rewrite.

#### Scenario: Suffixed query
- **WHEN** a valid suffixed `queryType` stored as a single item, such as `STANDINGS#2024`, is queried
- **THEN** the API returns the matching item's `data` with `200` via an exact `get_item`

#### Scenario: Suffixed chunked query
- **WHEN** a suffixed `queryType` for a chunked view, such as `TRANSACTIONS#2024`, is queried and the season spans multiple chunk items
- **THEN** the API returns every chunk item's `data` concatenated into one flat list with `200`, paginating over `LastEvaluatedKey`

#### Scenario: Suffixed chunked query with legacy single-key item
- **WHEN** a suffixed `TRANSACTIONS#{season}` query is made for a league whose season was written before chunking as a single `TRANSACTIONS#{season}` item
- **THEN** the API still returns that item's `data` with `200`, because the prefix query matches the legacy key

#### Scenario: No data for a suffixed query
- **WHEN** a valid suffixed `queryType` has no matching item (single or chunked)
- **THEN** the API returns `404` "No data found for the requested query"

### Requirement: Query an unsuffixed collection view
The API SHALL return all matching items' `data` concatenated and fully paginated for a valid unsuffixed `queryType`.

#### Scenario: Collection query paginates fully
- **WHEN** a bare `queryType` such as `MATCHUPS` is queried
- **THEN** the API returns all matching items via a `begins_with` prefix query, paginating over `LastEvaluatedKey` (not just the first page), with `200`

### Requirement: Validate query type and existence
The API SHALL reject an unrecognized `queryType`, and return `404` for an un-onboarded league or a valid query with no stored data. `queryType` matching SHALL be case-insensitive.

#### Scenario: Invalid query type
- **WHEN** an unrecognized `queryType` is requested
- **THEN** the API returns `400` with a documentation pointer

#### Scenario: League not onboarded
- **WHEN** the league is not in `LEAGUE_LOOKUP`
- **THEN** the API returns `404`

#### Scenario: No data for a valid query
- **WHEN** a valid query has no stored item
- **THEN** the API returns `404` "No data found for the requested query"

#### Scenario: Case-insensitive query type
- **WHEN** `queryType` is supplied in mixed case
- **THEN** it is matched case-insensitively

### Requirement: Serialize DynamoDB values safely
The API SHALL convert DynamoDB `Decimal` values to native JSON numbers before serialization.

#### Scenario: Decimal conversion
- **WHEN** a stored view contains `Decimal` values
- **THEN** they are converted to JSON-safe numbers in the response (`convert_decimals`)

### Requirement: Cache successful query responses
The API SHALL set `Cache-Control: private, max-age=300` on successful query responses.

#### Scenario: Cache header set
- **WHEN** a query succeeds
- **THEN** the response sets `Cache-Control: private, max-age=300`

### Requirement: Member-gated ESPN queries
The API SHALL gate ESPN queries to league members and leave Sleeper queries open to any authenticated caller.

#### Scenario: Non-member ESPN query
- **WHEN** a non-member queries an ESPN league
- **THEN** the API returns `403`

#### Scenario: Sleeper query open
- **WHEN** any authenticated caller queries a Sleeper league
- **THEN** the query is allowed

### Requirement: Expose the league settings view
The API SHALL serve the per-season league settings view through the `LEAGUE_SETTINGS` `queryType`, returning the stored `LEAGUE_SETTINGS#{season}` item's `data` for a season-suffixed query.

#### Scenario: League settings query
- **WHEN** `queryType=LEAGUE_SETTINGS#{season}` is queried for an onboarded league
- **THEN** the API returns the season's `num_playoff_teams`, `playoff_week_start`, and `regular_season_weeks` with `200`

#### Scenario: League settings missing
- **WHEN** `queryType=LEAGUE_SETTINGS#{season}` is queried and no such item exists
- **THEN** the API returns `404` "No data found for the requested query"
