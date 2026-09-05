# transactions Specification

## Purpose
The `/transactions` page lists a season's completed transactions — waivers, trades, and free-agent moves — for the connected league, newest first, with per-team adds (green) and drops (red). Below the season selector, a per-owner summary table breaks down activity for the selected season. Available for both Sleeper (waivers/trades/free agents, all seasons) and ESPN (waivers/free agents, current season only) leagues; the type filter is platform-aware (ESPN offers no Trades).

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

### Requirement: Trade rest-of-season points
For a two-team trade, `/transactions` SHALL show, for each acquired player, the total fantasy
points they scored from the trade's week through the end of the season (all games, following the
player regardless of later roster moves), plus a per-side total and which side scored more (or a
tie) — all computed client-side from the season's `MATCHUPS` box scores; when those box scores are
unavailable the trade SHALL render without these additions and without an error.

#### Scenario: Per-player points and winner
- **WHEN** a two-team trade is shown and the season's matchup box scores are available
- **THEN** each acquired player shows the sum of their `points_scored` for weeks on or after the
  trade's week, each side shows the total of its acquired players' points, and the higher-scoring
  side is marked as the winner with the point margin

#### Scenario: Points window excludes earlier weeks
- **WHEN** an acquired player scored in weeks before the trade's week and in weeks on or after it
- **THEN** only the points from the trade's week onward are counted toward that player's total

#### Scenario: Traded pick has no points
- **WHEN** a trade side receives a draft pick
- **THEN** the pick row shows no points value and is excluded from the side total

#### Scenario: Tie
- **WHEN** both sides of a trade have equal rest-of-season totals
- **THEN** the card shows a tie ("Even") rather than a winning side

#### Scenario: Box scores unavailable
- **WHEN** the season's matchup box scores fail to load or do not exist
- **THEN** the trade renders in its normal form with no points, totals, or winner, and no error
  banner is shown
