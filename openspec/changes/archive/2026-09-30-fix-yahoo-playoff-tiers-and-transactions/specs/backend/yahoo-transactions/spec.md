## MODIFIED Requirements

### Requirement: Fetch Yahoo transactions per onboarded season
Onboarding or refreshing a Yahoo league SHALL fetch the league's transactions for each onboarded
season (each Yahoo season is a distinct league), keeping only completed add/drop and trade
transactions.

#### Scenario: Transactions fetched for each season
- **WHEN** a Yahoo league with multiple onboarded seasons is onboarded
- **THEN** transactions are fetched for each season, and only completed add/drop and trade
  transactions are retained

#### Scenario: Season with no transactions
- **WHEN** a Yahoo season has no completed transactions
- **THEN** no `TRANSACTIONS#{season}` item is written for that season and the run does not error

### Requirement: Build the Yahoo transactions view
Processing a Yahoo season with completed transactions SHALL write the season's rows across one or
more size-bounded `TRANSACTIONS#{season}` items matching the shared transactions view schema. Each
row SHALL carry the transaction type (`waiver`/`free_agent`/`trade`), the week, the creation time
in epoch milliseconds, resolved player names/positions for adds and drops, resolved team labels,
the waiver bid amount when present, and an empty `draft_picks` list. Each stored item SHALL stay
within the DynamoDB per-item size limit.

#### Scenario: Adds, drops, and trades written with resolved names
- **WHEN** a Yahoo season with completed add/drop and trade transactions is processed
- **THEN** one or more `TRANSACTIONS#{season}` items are written whose rows carry the transaction
  type, resolved player names/positions, resolved team labels, and (for waivers) the bid amount

#### Scenario: Adds and drops attributed to the correct team
- **WHEN** a stored transaction moves a player to one team and drops another from a team
- **THEN** each added player is attributed to the receiving team and each dropped player to the
  releasing team

#### Scenario: Trade players attributed to both teams
- **WHEN** a stored trade moves players between two teams
- **THEN** each traded player appears as an add for the receiving team and as a drop for the
  sending team, and both teams are listed on the row

#### Scenario: Creation time in milliseconds
- **WHEN** a Yahoo transaction is processed
- **THEN** its `created` value is the transaction time in epoch milliseconds

#### Scenario: Week resolved from the season's week calendar
- **WHEN** a Yahoo season's week calendar is available
- **THEN** each transaction's `week` is the first week whose end date is on or after the
  transaction date, clamped to the season's first and last weeks

#### Scenario: Week calendar unavailable
- **WHEN** a Yahoo season has no week calendar
- **THEN** transactions are still written, with a null `week`

#### Scenario: Large season split across items
- **WHEN** a season has more stored transactions than fit in a single item under the DynamoDB
  per-item size limit
- **THEN** the rows are split across multiple size-bounded items with no row dropped or duplicated
