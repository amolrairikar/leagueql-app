# transactions Specification

## Purpose
The `/transactions` page lists a season's completed transactions — waivers, trades, and free-agent moves — for the connected league, newest first, with per-team adds (green) and drops (red). Below the season selector, a per-owner summary table breaks down activity for the selected season. This is a Sleeper-only feature; ESPN exposes no transaction data.

## Requirements

### Requirement: List the season's transactions
`/transactions` SHALL list the selected season's completed transactions newest-first, each showing type, week, date, per-team adds (green)/drops (red), and (for waivers) FAAB bid and traded draft picks.

#### Scenario: Transaction wire
- **WHEN** a season with transactions is selected
- **THEN** its completed transactions are listed newest-first with type, week, date, per-team adds/drops, waiver FAAB bids, and traded draft picks when present

#### Scenario: Unknown player
- **WHEN** a transaction references a player with no resolved name
- **THEN** it falls back to `Player {id}` and omits a missing position

### Requirement: Sleeper-only navigation
The Transactions nav item SHALL appear only for Sleeper leagues and be hidden for ESPN leagues.

#### Scenario: Nav gating
- **WHEN** the connected league's platform is `SLEEPER`
- **THEN** the Transactions sidebar item appears; for ESPN it is hidden

### Requirement: Season selector and type filter
The season selector SHALL list all onboarded seasons and default to the latest, and the type filter SHALL narrow the wire to All / Trades / Waivers / Free Agents.

#### Scenario: Select and filter
- **WHEN** the page loads
- **THEN** the season selector lists all onboarded seasons defaulting to the latest, and the type filter narrows the transaction wire by type

### Requirement: Empty and error states
A season with no transactions SHALL show an empty state and a load error SHALL show an inline error (no global banner).

#### Scenario: Empty season
- **WHEN** the season has no completed transactions (API 404s)
- **THEN** an empty state renders (404 mapped to an empty list), not an error

#### Scenario: Load failure
- **WHEN** a non-404 failure occurs
- **THEN** it surfaces inline via the shared `Result`/`toResult` pattern

### Requirement: Per-owner summary table
The summary SHALL list one row per participating owner with per-transaction Waivers, Free Agents, Trades, and Total counts, ordered by Total descending, reusing Season Standings avatars, and rendering nothing on an empty/failed load.

#### Scenario: Summary counts
- **WHEN** the summary renders for a season with transactions
- **THEN** it lists one row per owner appearing in the season's transactions, with per-transaction Waivers/Free Agents/Trades/Total counts (each transaction adds 1 per involved owner, commissioner moves excluded), ordered by Total descending (owner name A–Z tie-break)

#### Scenario: Avatar reuse and fallback
- **WHEN** the season's `SEASON_STANDINGS` view loads
- **THEN** each summary row reuses the owner's Season Standings avatar logo and positional color (joined on roster id); when standings is missing/failed or omits a roster, the row falls back to an index-based color and initials

#### Scenario: Summary on empty/error
- **WHEN** the season has no transactions or the load fails
- **THEN** the summary table renders nothing and the wire shows the empty/error message
