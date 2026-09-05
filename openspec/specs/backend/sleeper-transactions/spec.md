# sleeper-transactions Specification

## Purpose
Build a precomputed transactions view for Sleeper leagues — completed waiver claims, trades (players and/or draft picks), free-agent adds/drops, and commissioner moves — with opaque Sleeper player IDs resolved to names/positions and roster IDs resolved to team labels. The processor writes it to DynamoDB and it is read through the query API under `queryType=TRANSACTIONS#{season}`. This capability covers the Sleeper producer; ESPN transactions are produced by `backend/espn-transactions` into the same `TRANSACTIONS#{season}` items.

## Requirements

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

### Requirement: Resolve players and rosters gracefully
The processor SHALL tolerate unknown players and unresolvable rosters without failing the run.

#### Scenario: Unknown player
- **WHEN** a player ID is absent from the cached Sleeper player metadata
- **THEN** the row resolves to `player_name = null` (position may be null) and still writes

#### Scenario: Unresolvable roster
- **WHEN** a roster in `roster_ids` cannot be resolved to a team
- **THEN** it falls back to a `Roster {id}` label

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

### Requirement: Backfill existing leagues idempotently
The backfill script SHALL re-onboard every Sleeper league with `reprocess_all` (via REFRESH, preserving METADATA), rebuilding transactions for all seasons, and SHALL be idempotent.

#### Scenario: Backfill run
- **WHEN** the backfill script runs with `--execute`
- **THEN** it invokes the onboarder in `REFRESH` mode with `reprocess_all=True` for each Sleeper league (preserving owner/members), rebuilding transactions for all seasons from S3, and running it twice produces the same result
