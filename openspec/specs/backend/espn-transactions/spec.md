# espn-transactions Specification

## Purpose
Build a precomputed transactions view for ESPN leagues — the current season's completed waiver claims, free-agent adds/drops, and trades (with traded players hidden by `mTransactions2` recovered from player cards) — with ESPN player IDs resolved to names/positions and team IDs resolved to team labels. The processor writes it to DynamoDB and it is read through the query API under `queryType=TRANSACTIONS#{season}`.

## Requirements

### Requirement: Fetch ESPN transactions for the current season only
Onboarding or refreshing an ESPN league SHALL fetch transactions from the `mTransactions2` view for the latest (current) season only, issuing one request per scoring period (week) up to and including the season's current scoring period — each request carrying that week's `scoringPeriodId` — because a `mTransactions2` request without a `scoringPeriodId` returns only the current scoring period's transactions, and a request for any scoring period at or beyond the current one returns (and would duplicate) the current period's transactions. When the current scoring period is unknown, the system MAY request the full week range and SHALL rely on deduplication to keep each transaction once. The per-week payloads SHALL be combined into the season's transactions view, with each transaction stored exactly once regardless of how many per-week requests returned it. The system SHALL NOT request transactions for any earlier season.

#### Scenario: Only the latest season is requested
- **WHEN** an ESPN league with multiple onboarded seasons is fetched and the latest season's current scoring period is known
- **THEN** transactions requests are issued only for the latest season, one per scoring period from week 1 through the current scoring period, and no transactions request is issued for any earlier season or for any week beyond the current scoring period

#### Scenario: Transactions across multiple weeks are all captured
- **WHEN** the latest season has completed transactions in more than one scoring period (e.g. weeks 1, 2, and 3)
- **THEN** the season's transactions view contains the stored transactions from every one of those weeks, not only the most recent scoring period

#### Scenario: A transaction returned by more than one week is stored once
- **WHEN** the same transaction is returned by more than one per-week request (for example the current period's transactions echoed by a request at or beyond the current scoring period)
- **THEN** that transaction appears exactly once in the season's transactions view

#### Scenario: No transactions request when the latest season is undrafted
- **WHEN** an ESPN league's latest season has not yet drafted (it produces no data and is excluded)
- **THEN** no transactions request is issued for any week

#### Scenario: Weeks with no transactions are tolerated
- **WHEN** a scoring period of the latest season returns no transactions
- **THEN** that week contributes no rows and the run succeeds, combining the remaining weeks' transactions into the season's view

### Requirement: Build the ESPN transactions view
Processing an ESPN league whose current season has completed transactions SHALL write the season's rows across one or more size-bounded `TRANSACTIONS#{season}#{chunk}` items, keeping only `EXECUTED` transactions of type `FREEAGENT` (stored as `free_agent`), `WAIVER` (stored as `waiver`), and `TRADE_UPHOLD` or `TRADE_ACCEPT` (stored as `trade`). Each row SHALL carry resolved player names/positions and team labels, an empty `draft_picks` list, and the waiver bid amount. A trade's records SHALL be grouped into one trade by `relatedTransactionId` (or the record's `id` when there is none, or the traded items and `processDate` for records carrying neither link), and each completed trade SHALL be stored as one row: each traded player recorded as a drop from its source team and an add to its destination team, players released to make room recorded as drops, both trading teams (taken from the trade's items) listed in `roster_ids`/`teams`, and `created` taken from the upholding (else accepting) record's `processDate`, else `acceptedDate`, else `proposedDate`. A trade with no recoverable traded players SHALL NOT be stored. Each item's stored payload SHALL stay within the DynamoDB per-item size limit regardless of how many transactions a season contains.

#### Scenario: Waivers and free agents written with resolved names
- **WHEN** an ESPN current season with EXECUTED waiver claims and free-agent adds/drops is processed
- **THEN** one or more `TRANSACTIONS#{season}#{chunk}` items are written with rows typed `waiver`/`free_agent`, carrying resolved player names/positions, team labels, and (for waivers) the bid amount

#### Scenario: Upheld trade written for both teams
- **WHEN** an ESPN current season has an EXECUTED `TRADE_UPHOLD` whose items move players between two teams (and whose `teamId` is a third team)
- **THEN** a row typed `trade` is written listing both trading teams with resolved labels, each traded player as a drop from its source team and an add to its destination team, and `created` equal to the trade's `processDate`

#### Scenario: Hidden trade filled from a player-card accept
- **WHEN** an EXECUTED `TRADE_UPHOLD` with no items and no `processDate` and a player-card EXECUTED `TRADE_ACCEPT` with `TRADE` items share a `relatedTransactionId`
- **THEN** exactly one `trade` row is written, carrying the uphold's transaction ID, the accept's traded players, and the uphold's `proposedDate` as `created`

#### Scenario: Accepted trade without a review period
- **WHEN** an ESPN current season has an EXECUTED `TRADE_ACCEPT` with traded players and no `TRADE_UPHOLD` for that trade
- **THEN** one row typed `trade` is written for it

#### Scenario: Accept and uphold of the same trade stored once
- **WHEN** an EXECUTED `TRADE_ACCEPT` and an EXECUTED `TRADE_UPHOLD` with no `relatedTransactionId` carry the same trade items and `processDate`
- **THEN** exactly one `trade` row is written for that trade, carrying the uphold's transaction ID

#### Scenario: Trade without recoverable players is not stored
- **WHEN** an EXECUTED `TRADE_UPHOLD` has no traded players and no record in its group supplies them
- **THEN** no `trade` row is written for it

#### Scenario: Non-stored types and statuses are dropped
- **WHEN** the raw transactions include DRAFT, ROSTER (lineup) moves, `TRADE_PROPOSAL` records, or records whose status is not `EXECUTED` (such as a pending or status-less `TRADE_ACCEPT` or a cancelled proposal)
- **THEN** those are dropped and only EXECUTED waivers, free agents, and trades are stored

#### Scenario: Adds and drops attributed to the correct team
- **WHEN** a stored transaction has add items (to a team) and drop items (from a team)
- **THEN** each added player is attributed to the receiving team and each dropped player to the releasing team

#### Scenario: Large season split across chunks
- **WHEN** a season has more stored transactions than fit in a single item under the DynamoDB per-item size limit
- **THEN** the rows are split across multiple `TRANSACTIONS#{season}#{chunk}` items, each within the size limit, and no row is dropped or duplicated

### Requirement: Recover hidden ESPN trade details from player cards
When a fetched week of the latest season contains an EXECUTED `TRADE_UPHOLD` or `TRADE_ACCEPT` with no traded players (because `mTransactions2` hides the players of trades that don't involve the requesting team), the onboarder SHALL fetch the `kona_playercard` view for the players rostered in that week and the following week, in batches of at most 40 player IDs, and SHALL store, alongside the season's transactions, the EXECUTED `TRADE_ACCEPT` from those cards that carries the most traded players for each hidden trade (matched by `relatedTransactionId`, or by `id` when there is none). A failed player-card request SHALL be logged and SHALL NOT fail the onboarding or refresh.

#### Scenario: Hidden trade recovered from player cards
- **WHEN** week 4 of the latest season returns an EXECUTED `TRADE_UPHOLD` with no items whose `relatedTransactionId` is `T1`, and a rostered player's card lists an EXECUTED `TRADE_ACCEPT` with `relatedTransactionId` `T1` and `TRADE` items
- **THEN** the player cards of the players rostered in weeks 4 and 5 are requested in batches of at most 40, and that `TRADE_ACCEPT` is stored with the season's transactions

#### Scenario: No card requests without a hidden trade
- **WHEN** no fetched week contains an executed trade record without traded players
- **THEN** no `kona_playercard` request is made

#### Scenario: Card request failure is tolerated
- **WHEN** a `kona_playercard` request fails
- **THEN** a warning is logged, the onboarding or refresh still succeeds, and the hidden trade it would have filled is not stored

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
