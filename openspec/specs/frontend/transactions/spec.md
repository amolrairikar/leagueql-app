# transactions Specification

## Purpose
The `/transactions` page lists a season's completed transactions — waivers, trades, and free-agent moves — for the connected league, newest first, with per-team adds (green) and drops (red). Below the season selector, a per-owner summary table breaks down activity for the selected season. Available for both Sleeper (waivers/trades/free agents, all seasons) and ESPN (waivers/free agents, 2026 season onward only — the ESPN API returns no historical transactions, so the page carries a disclaimer to that effect) leagues; the type filter is platform-aware (ESPN offers no Trades).

## Requirements

### Requirement: List the season's transactions
`/transactions` SHALL list the selected season's completed transactions newest-first, each showing type, week, date, per-team adds (green)/drops (red), and (for waivers) FAAB bid and traded draft picks.

#### Scenario: Transaction wire
- **WHEN** a season with transactions is selected
- **THEN** its completed transactions are listed newest-first with type, week, date, per-team adds/drops, waiver FAAB bids, and traded draft picks when present

#### Scenario: Unknown player
- **WHEN** a transaction references a player with no resolved name
- **THEN** it falls back to `Player {id}` and omits a missing position

### Requirement: Transactions navigation
The Transactions nav item SHALL appear for both Sleeper and ESPN leagues.

#### Scenario: Nav shown for Sleeper
- **WHEN** the connected league's platform is `SLEEPER`
- **THEN** the Transactions sidebar item appears

#### Scenario: Nav shown for ESPN
- **WHEN** the connected league's platform is `ESPN`
- **THEN** the Transactions sidebar item appears

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

### Requirement: ESPN historical-transactions disclaimer
The `/transactions` page SHALL display a disclaimer at the top for ESPN leagues only, marked with an asterisk, stating that the ESPN API does not return historical transactions so only transactions from the 2026 fantasy season and onward are stored. The disclaimer SHALL NOT appear for non-ESPN (e.g. Sleeper) leagues.

#### Scenario: Disclaimer shown for ESPN
- **WHEN** the connected league's platform is `ESPN` and the `/transactions` page is viewed
- **THEN** an asterisked disclaimer is shown at the top explaining that the ESPN API does not return historical transactions and only 2026-and-onward transactions are stored

#### Scenario: No disclaimer for Sleeper
- **WHEN** the connected league's platform is `SLEEPER` and the `/transactions` page is viewed
- **THEN** no such disclaimer is shown

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
points they scored while on the receiving roster — from the trade's week up to (not including) the
week of the next season transaction of any type that drops that player from that roster, or through
the end of the season when there is none — plus a per-side total (labelled "Points while rostered")
and which side scored more (or a tie), all computed client-side from the season's `MATCHUPS` box
scores; when those box scores are unavailable the trade SHALL render without these additions and
without an error.

#### Scenario: Per-player points and winner
- **WHEN** a two-team trade is shown and the season's matchup box scores are available
- **THEN** each acquired player shows the sum of their `points_scored` for weeks on or after the
  trade's week while on the receiving roster, each side shows the total of its acquired players'
  points, and the higher-scoring side is marked as the winner with the point margin

#### Scenario: Points window excludes earlier weeks
- **WHEN** an acquired player scored in weeks before the trade's week and in weeks on or after it
- **THEN** only the points from the trade's week onward are counted toward that player's total

#### Scenario: Acquired player later dropped or traded away
- **WHEN** a player acquired in a trade is later dropped or traded away from the receiving roster
- **THEN** only the points from the trade's week up to (not including) that later transaction's
  week count toward the player's total, the side total, and the winning margin

#### Scenario: Traded pick has no points
- **WHEN** a trade side receives a draft pick
- **THEN** the pick row shows no points value and is excluded from the side total

#### Scenario: Tie
- **WHEN** both sides of a trade have equal totals
- **THEN** the card shows a tie ("Even") rather than a winning side

#### Scenario: Box scores unavailable
- **WHEN** the season's matchup box scores fail to load or do not exist
- **THEN** the trade renders in its normal form with no points, totals, or winner, and no error
  banner is shown

### Requirement: Waiver and free-agent rest-of-season points
For a waiver or free-agent move, `/transactions` SHALL show, for each added player, the total
fantasy points that player scored while on the acquiring roster — from the transaction's week up to
(not including) the week of the next season transaction of any type that drops that player from
that roster, or through the end of the season when there is none — and, for each dropped player,
the total fantasy points that player scored from the transaction's week through the end of the
season (all games, following the player regardless of later roster moves), all computed
client-side from the season's `MATCHUPS` box scores. The per-player points column SHALL be headed
"Points while rostered". Every waiver or free-agent move SHALL also show a net pickup value equal to
the added players' total minus the dropped players' total: a move with both an add and a drop shows
their difference, a pure add resolves to the added total, and a pure drop resolves to the negative
of the dropped total. When the season's matchup box scores are unavailable, the move SHALL render
in its normal form with no points, no net value, and no error.

#### Scenario: Per-player points and net pickup value
- **WHEN** a waiver or free-agent move with both an add and a drop is shown and the season's
  matchup box scores are available
- **THEN** the added player shows the sum of their `points_scored` for weeks on or after the
  transaction's week while on the acquiring roster, the dropped player shows the sum of their
  `points_scored` for weeks on or after the transaction's week, the points column is headed
  "Points while rostered", and the card shows a net pickup value equal to the added total minus the
  dropped total (positive when the add outscored the drop, negative when the drop outscored the
  add, "Even" when equal)

#### Scenario: Points window excludes earlier weeks
- **WHEN** an added or dropped player scored in weeks before the transaction's week and in weeks on
  or after it
- **THEN** only the points from the transaction's week onward are counted toward that player's total

#### Scenario: Added player later dropped
- **WHEN** an added player is dropped from the same roster by a later waiver or free-agent move
- **THEN** only the points from the original transaction's week up to (not including) the later
  drop's week count toward the added player's total and the net pickup value

#### Scenario: Added player later traded away
- **WHEN** an added player is later traded away from the acquiring roster
- **THEN** the added player's total stops before the trade's week

#### Scenario: Added player dropped in the same week
- **WHEN** an added player is dropped from the same roster by a later transaction in the same week
- **THEN** the added player's total is 0

#### Scenario: Dropped player keeps full rest of season
- **WHEN** a waiver or free-agent move drops a player
- **THEN** the dropped player's total counts every week from the transaction's week through the end
  of the season, regardless of that player's later roster moves

#### Scenario: Pure add
- **WHEN** a waiver or free-agent move has an add and no drop
- **THEN** the added player shows their points while rostered and the net pickup value equals the
  added player's total

#### Scenario: Pure drop
- **WHEN** a waiver or free-agent move has a drop and no add
- **THEN** the dropped player shows their rest-of-season points and the net pickup value equals the
  negative of the dropped player's total

#### Scenario: Box scores unavailable for a waiver or free agent
- **WHEN** the season's matchup box scores fail to load or do not exist
- **THEN** the waiver or free-agent move renders in its normal form with no points, no net value,
  and no error banner is shown

### Requirement: Highlight the season's top transactions
`/transactions` SHALL show a "Top transactions" section above the Summary table listing up to five
of the selected season's highest-impact moves across waivers, free agents, and trades together,
ordered by impact descending (earlier transaction first on a tie). A waiver or free-agent move's
impact SHALL be its net pickup value, and a two-team trade's impact SHALL be its winning margin,
credited to the winning team — both computed from the season's `MATCHUPS` box scores exactly as the
transaction cards compute them. Only moves with a positive impact SHALL be eligible; multi-team
trades and commissioner moves are never eligible. The section SHALL NOT change with the type
filter, and SHALL render nothing when no move is eligible or the matchup box scores are unavailable.

#### Scenario: Top moves across types
- **WHEN** a season has eligible waiver, free-agent, and trade moves and matchup box scores are
  available
- **THEN** the section shows at most five tiles ranked by impact descending, each with its rank,
  type, impact value, team, and the players added/dropped (for a trade, what the winning team
  received and gave up)

#### Scenario: Trade tile credits the winner
- **WHEN** an eligible two-team trade appears in the section
- **THEN** its tile shows the winning team, its winning margin labelled as won-by, and the losing
  team as the opponent

#### Scenario: Fewer than five eligible
- **WHEN** fewer than five moves have a positive impact
- **THEN** only those moves are shown; even trades and net-zero or net-negative pickups are omitted

#### Scenario: Nothing eligible
- **WHEN** no move in the season has a positive impact
- **THEN** the "Top transactions" section is not rendered

#### Scenario: Box scores unavailable
- **WHEN** the season's matchup box scores fail to load or do not exist
- **THEN** the "Top transactions" section is not rendered and the rest of the page renders normally
  without an error

#### Scenario: Independent of the type filter
- **WHEN** the user changes the type filter
- **THEN** the "Top transactions" section is unchanged
