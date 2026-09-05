## MODIFIED Requirements

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
