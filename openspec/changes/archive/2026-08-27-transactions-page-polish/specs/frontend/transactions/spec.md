# transactions Specification

## MODIFIED Requirements

### Requirement: Season selector and type filter
The season selector SHALL list all onboarded seasons and default to the latest, and the type
filter SHALL narrow the wire to Trades / Waivers / Free Agents, defaulting to Trades (there is
no "All" option).

#### Scenario: Select and filter
- **WHEN** the page loads
- **THEN** the season selector lists all onboarded seasons defaulting to the latest, and the
  type filter defaults to Trades and narrows the transaction wire to the selected type

#### Scenario: Default shows trades
- **WHEN** the page first renders a season with transactions
- **THEN** only trade transactions are listed and the Trades filter is the selected option, with
  no "All" option offered

#### Scenario: Narrow to another type
- **WHEN** the Waivers or Free Agents filter is selected
- **THEN** the wire narrows to only that type's transactions
