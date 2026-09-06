## ADDED Requirements

### Requirement: Transactions navigation
The Transactions nav item SHALL appear for both Sleeper and ESPN leagues.

#### Scenario: Nav shown for Sleeper
- **WHEN** the connected league's platform is `SLEEPER`
- **THEN** the Transactions sidebar item appears

#### Scenario: Nav shown for ESPN
- **WHEN** the connected league's platform is `ESPN`
- **THEN** the Transactions sidebar item appears

## MODIFIED Requirements

### Requirement: Season selector and type filter
The season selector SHALL list all onboarded seasons and default to the latest. The type filter
SHALL be platform-aware: for Sleeper it offers Trades / Waivers / Free Agents and defaults to
Trades; for ESPN it offers only Waivers / Free Agents (no Trades, which ESPN does not produce) and
defaults to Free Agents. There is no "All" option on either platform.

#### Scenario: Select and filter
- **WHEN** the page loads
- **THEN** the season selector lists all onboarded seasons defaulting to the latest, and the type
  filter defaults to the platform's default type and narrows the transaction wire to the selected
  type

#### Scenario: Default shows trades
- **WHEN** a Sleeper page first renders a season with transactions
- **THEN** only trade transactions are listed and the Trades filter is the selected option, with no
  "All" option offered

#### Scenario: ESPN defaults to free agents
- **WHEN** an ESPN page first renders a season with transactions
- **THEN** the type filter offers only Waivers / Free Agents, defaults to Free Agents, only
  free-agent transactions are listed, and no Trades or "All" option is offered

#### Scenario: Narrow to another type
- **WHEN** a different available filter (Waivers, Free Agents, or — for Sleeper — Trades) is selected
- **THEN** the wire narrows to only that type's transactions

## REMOVED Requirements

### Requirement: Sleeper-only navigation
**Reason**: ESPN now produces transaction data (`backend/espn-transactions`), so the nav item is no
longer Sleeper-gated. Replaced by the "Transactions navigation" requirement above.
**Migration**: None — the nav item simply becomes visible for ESPN leagues as well.
