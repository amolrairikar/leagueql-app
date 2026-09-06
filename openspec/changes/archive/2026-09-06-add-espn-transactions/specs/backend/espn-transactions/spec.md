## Purpose
Build a precomputed transactions view for ESPN leagues — the current season's completed waiver claims and free-agent adds/drops — with ESPN player IDs resolved to names/positions and team IDs resolved to team labels. The processor writes it to DynamoDB and it is read through the query API under `queryType=TRANSACTIONS#{season}`.

## ADDED Requirements

### Requirement: Fetch ESPN transactions for the current season only
Onboarding or refreshing an ESPN league SHALL fetch transactions from the `mTransactions2` view for the latest (current) season only, in a single request per league, and SHALL NOT request transactions for any earlier season.

#### Scenario: Only the latest season is requested
- **WHEN** an ESPN league with multiple onboarded seasons is fetched
- **THEN** a transactions request is issued for the latest season only, and no transactions request is issued for earlier seasons

#### Scenario: No transactions request when the latest season is undrafted
- **WHEN** an ESPN league's latest season has not yet drafted (it produces no data and is excluded)
- **THEN** no transactions request is issued

### Requirement: Build the ESPN transactions view
Processing an ESPN league whose current season has completed transactions SHALL write the season's rows across one or more size-bounded `TRANSACTIONS#{season}#{chunk}` items, keeping only `EXECUTED` transactions of type `FREEAGENT` (stored as `free_agent`) and `WAIVER` (stored as `waiver`). Each row SHALL carry resolved player names/positions and team labels, an empty `draft_picks` list, and the waiver bid amount. Each item's stored payload SHALL stay within the DynamoDB per-item size limit regardless of how many transactions a season contains.

#### Scenario: Waivers and free agents written with resolved names
- **WHEN** an ESPN current season with EXECUTED waiver claims and free-agent adds/drops is processed
- **THEN** one or more `TRANSACTIONS#{season}#{chunk}` items are written with rows typed `waiver`/`free_agent`, carrying resolved player names/positions, team labels, and (for waivers) the bid amount

#### Scenario: Non-stored types and statuses are dropped
- **WHEN** the raw transactions include DRAFT, ROSTER (lineup) moves, trade types, or records whose status is not `EXECUTED`
- **THEN** those are dropped and only EXECUTED waivers and free agents are stored

#### Scenario: Adds and drops attributed to the correct team
- **WHEN** a stored transaction has add items (to a team) and drop items (from a team)
- **THEN** each added player is attributed to the receiving team and each dropped player to the releasing team

#### Scenario: Large season split across chunks
- **WHEN** a season has more stored transactions than fit in a single item under the DynamoDB per-item size limit
- **THEN** the rows are split across multiple `TRANSACTIONS#{season}#{chunk}` items, each within the size limit, and no row is dropped or duplicated

### Requirement: Resolve players and teams gracefully
The processor SHALL tolerate unknown players and unresolvable teams without failing the run.

#### Scenario: Unknown player
- **WHEN** a player ID is absent from the season's player metadata
- **THEN** the row resolves to `player_name = null` (position may be null) and still writes

#### Scenario: Unresolvable team
- **WHEN** a team ID cannot be resolved to a team
- **THEN** the row still writes with null team labels for that team

### Requirement: No item for empty transactions
An ESPN league whose current season has no stored transactions SHALL write no `TRANSACTIONS#{season}` item (of any chunk).

#### Scenario: No transactions
- **WHEN** an ESPN current season has no EXECUTED waiver or free-agent transactions
- **THEN** no `TRANSACTIONS#{season}` item (of any chunk) is written and a query for it returns `404`

### Requirement: Serve ESPN transactions through the query API
`GET /leagues/{leagueId}/query?platform=ESPN&queryType=TRANSACTIONS#{season}` SHALL return the season's rows, concatenated across every chunk item for that season.

#### Scenario: Query transactions
- **WHEN** a client queries `TRANSACTIONS#{season}` for an ESPN league
- **THEN** the season's transaction rows are returned, gathering all chunk items for that season into one flat list
