## MODIFIED Requirements

### Requirement: Build the ESPN transactions view
Processing an ESPN league whose current season has completed transactions SHALL write the season's rows across one or more size-bounded `TRANSACTIONS#{season}#{chunk}` items, keeping only `EXECUTED` transactions of type `FREEAGENT` (stored as `free_agent`), `WAIVER` (stored as `waiver`), and `TRADE_UPHOLD` or `TRADE_ACCEPT` (stored as `trade`). Each row SHALL carry resolved player names/positions and team labels, an empty `draft_picks` list, and the waiver bid amount. A trade row SHALL record each traded player as a drop from its source team and an add to its destination team, list both trading teams (taken from the trade's items) in `roster_ids`/`teams`, and use the trade's execution time (`processDate`) as `created`; a trade recorded by both an EXECUTED `TRADE_ACCEPT` and an EXECUTED `TRADE_UPHOLD` SHALL be stored once. Each item's stored payload SHALL stay within the DynamoDB per-item size limit regardless of how many transactions a season contains.

#### Scenario: Waivers and free agents written with resolved names
- **WHEN** an ESPN current season with EXECUTED waiver claims and free-agent adds/drops is processed
- **THEN** one or more `TRANSACTIONS#{season}#{chunk}` items are written with rows typed `waiver`/`free_agent`, carrying resolved player names/positions, team labels, and (for waivers) the bid amount

#### Scenario: Upheld trade written for both teams
- **WHEN** an ESPN current season has an EXECUTED `TRADE_UPHOLD` whose items move players between two teams (and whose `teamId` is a third team)
- **THEN** a row typed `trade` is written listing both trading teams with resolved labels, each traded player as a drop from its source team and an add to its destination team, and `created` equal to the trade's `processDate`

#### Scenario: Accepted trade without a review period
- **WHEN** an ESPN current season has an EXECUTED `TRADE_ACCEPT` and no `TRADE_UPHOLD` for that trade
- **THEN** one row typed `trade` is written for it

#### Scenario: Accept and uphold of the same trade stored once
- **WHEN** an EXECUTED `TRADE_ACCEPT` and an EXECUTED `TRADE_UPHOLD` carry the same trade items and `processDate`
- **THEN** exactly one `trade` row is written for that trade, carrying the uphold's transaction ID

#### Scenario: Non-stored types and statuses are dropped
- **WHEN** the raw transactions include DRAFT, ROSTER (lineup) moves, `TRADE_PROPOSAL` records, or records whose status is not `EXECUTED` (such as a pending `TRADE_ACCEPT` or a cancelled proposal)
- **THEN** those are dropped and only EXECUTED waivers, free agents, and trades are stored

#### Scenario: Adds and drops attributed to the correct team
- **WHEN** a stored transaction has add items (to a team) and drop items (from a team)
- **THEN** each added player is attributed to the receiving team and each dropped player to the releasing team

#### Scenario: Large season split across chunks
- **WHEN** a season has more stored transactions than fit in a single item under the DynamoDB per-item size limit
- **THEN** the rows are split across multiple `TRANSACTIONS#{season}#{chunk}` items, each within the size limit, and no row is dropped or duplicated
