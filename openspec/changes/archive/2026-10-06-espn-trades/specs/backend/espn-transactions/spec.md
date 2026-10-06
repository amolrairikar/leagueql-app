## ADDED Requirements

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

## MODIFIED Requirements

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
