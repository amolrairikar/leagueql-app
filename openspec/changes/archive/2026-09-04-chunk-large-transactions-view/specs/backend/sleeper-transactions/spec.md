## MODIFIED Requirements

### Requirement: Build the transactions view
Processing a Sleeper league with transactions SHALL write the season's rows across one or more size-bounded `TRANSACTIONS#{season}#{chunk}` items whose rows include resolved player names and team labels, including only completed transactions. Each item's stored payload SHALL stay within the DynamoDB per-item size limit regardless of how many transactions a season contains.

#### Scenario: Transactions written with resolved names
- **WHEN** a Sleeper league with completed transactions is processed
- **THEN** one or more `TRANSACTIONS#{season}#{chunk}` items are written with rows carrying resolved player names/positions and team labels

#### Scenario: Large season split across chunks
- **WHEN** a Sleeper season has more completed transactions than fit in a single item under the DynamoDB per-item size limit
- **THEN** the rows are split across multiple `TRANSACTIONS#{season}#{chunk}` items, each within the size limit, and no row is dropped or duplicated

#### Scenario: Small season fits one chunk
- **WHEN** a Sleeper season's completed transactions fit within a single item under the size limit
- **THEN** exactly one `TRANSACTIONS#{season}#{chunk}` item is written containing all the season's rows

#### Scenario: Only completed transactions
- **WHEN** raw transaction data includes records with `status != "complete"` (e.g. failed waivers)
- **THEN** those are dropped and only completed waivers, trades, and free agents are included

#### Scenario: Trades with draft picks
- **WHEN** a trade carries draft picks
- **THEN** `draft_picks` are populated with correct from/to roster IDs (Sleeper `previous_owner_id → from_roster_id`, `owner_id → to_roster_id`)

### Requirement: No item for empty transactions
A Sleeper league/season with no completed transactions SHALL write no `TRANSACTIONS#{season}` item (of any chunk), and ESPN leagues SHALL never produce one.

#### Scenario: No transactions
- **WHEN** a Sleeper season has no completed transactions
- **THEN** no `TRANSACTIONS#{season}` item (of any chunk) is written and a query for it returns `404`

#### Scenario: ESPN league
- **WHEN** an ESPN league is processed
- **THEN** no `TRANSACTIONS` item is produced

### Requirement: Serve transactions through the query API
`GET /leagues/{leagueId}/query?platform=SLEEPER&queryType=TRANSACTIONS#{season}` SHALL return the season's rows, concatenated across every chunk item for that season.

#### Scenario: Query transactions
- **WHEN** a client queries `TRANSACTIONS#{season}` for a Sleeper league
- **THEN** the season's transaction rows are returned, gathering all chunk items for that season into one flat list
