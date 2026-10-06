## REMOVED Requirements

### Requirement: Season selector and type filter
**Reason**: ESPN now produces trades, so the platform-aware filter (ESPN without Trades, defaulting to Free Agents) no longer applies.
**Migration**: Replaced by "Season selector and platform-wide type filter", which offers Trades / Waivers / Free Agents on every platform.

## ADDED Requirements

### Requirement: Season selector and platform-wide type filter
The season selector SHALL list all onboarded seasons and default to the latest. The type filter
SHALL offer Trades / Waivers / Free Agents and default to Trades on every platform (Sleeper, ESPN,
and Yahoo). There is no "All" option.

#### Scenario: Select and filter
- **WHEN** the page loads
- **THEN** the season selector lists all onboarded seasons defaulting to the latest, and the type
  filter defaults to Trades and narrows the transaction wire to the selected type

#### Scenario: Default shows trades
- **WHEN** a page first renders a season with transactions
- **THEN** only trade transactions are listed and the Trades filter is the selected option, with no
  "All" option offered

#### Scenario: ESPN offers trades
- **WHEN** an ESPN page first renders a season with transactions
- **THEN** the type filter offers Trades / Waivers / Free Agents, defaults to Trades, and lists the
  season's ESPN trades

#### Scenario: Narrow to another type
- **WHEN** a different filter (Trades, Waivers, or Free Agents) is selected
- **THEN** the wire narrows to only that type's transactions
