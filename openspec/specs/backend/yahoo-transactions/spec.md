# yahoo-transactions Specification

## Purpose
Build a precomputed transactions view for Yahoo leagues — completed adds, drops, and trades — with
Yahoo player keys resolved to names/positions and team keys resolved to team labels. The processor
writes it to DynamoDB and it is read through the query API under `queryType=TRANSACTIONS#{season}`,
matching the ESPN and Sleeper transactions views.

## Requirements

### Requirement: Fetch Yahoo transactions per onboarded season
Onboarding or refreshing a Yahoo league SHALL fetch the league's transactions from the Yahoo
`transactions` resource for each onboarded season's `league_key` (each Yahoo season is a distinct
league key), keeping only completed add/drop and trade transactions.

#### Scenario: Transactions fetched for each season
- **WHEN** a Yahoo league with multiple onboarded seasons is onboarded
- **THEN** a transactions request is issued for each season's `league_key`, and only completed
  add/drop and trade transactions are retained

#### Scenario: Season with no transactions
- **WHEN** a Yahoo season has no completed transactions
- **THEN** no `TRANSACTIONS#{season}` item is written for that season and the run does not error

### Requirement: Build the Yahoo transactions view
Processing a Yahoo season with completed transactions SHALL write the season's rows across one or
more size-bounded `TRANSACTIONS#{season}` items matching the shared transactions view schema. Each
row SHALL carry the transaction type (`waiver`/`free_agent`/`trade`), the week, resolved player
names/positions for adds and drops, resolved team labels, the waiver bid amount when present, and
an empty `draft_picks` list. Each stored item SHALL stay within the DynamoDB per-item size limit.

#### Scenario: Adds, drops, and trades written with resolved names
- **WHEN** a Yahoo season with completed add/drop and trade transactions is processed
- **THEN** one or more `TRANSACTIONS#{season}` items are written whose rows carry the transaction
  type, resolved player names/positions, resolved team labels, and (for waivers) the bid amount

#### Scenario: Adds and drops attributed to the correct team
- **WHEN** a stored transaction moves a player to one team and drops another from a team
- **THEN** each added player is attributed to the receiving team and each dropped player to the
  releasing team

#### Scenario: Large season split across items
- **WHEN** a season has more stored transactions than fit in a single item under the DynamoDB
  per-item size limit
- **THEN** the rows are split across multiple size-bounded items with no row dropped or duplicated

### Requirement: Resolve players and teams gracefully
The processor SHALL tolerate unknown Yahoo players and unresolvable teams without failing the run.

#### Scenario: Unknown player falls back to null
- **WHEN** a transaction references a player key that cannot be resolved to a name/position
- **THEN** the row is written with a null player name rather than failing the run
