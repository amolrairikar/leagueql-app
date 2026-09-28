## MODIFIED Requirements

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
