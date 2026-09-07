## ADDED Requirements

### Requirement: Waiver and free-agent rest-of-season points
For a waiver or free-agent move, `/transactions` SHALL show, for each added and each dropped
player, the total fantasy points that player scored from the transaction's week through the end of
the season (all games, following the player regardless of later roster moves) — computed
client-side from the season's `MATCHUPS` box scores. When the move has both an add and a drop, the
card SHALL also show a net pickup value equal to the added players' total minus the dropped
players' total. A move with only an add or only a drop SHALL show that player's points with no net
value. When the season's matchup box scores are unavailable, the move SHALL render in its normal
form with no points, no net value, and no error.

#### Scenario: Per-player points and net pickup value
- **WHEN** a waiver or free-agent move with both an add and a drop is shown and the season's
  matchup box scores are available
- **THEN** the added player shows the sum of their `points_scored` for weeks on or after the
  transaction's week, the dropped player shows the same for their row, and the card shows a net
  pickup value equal to the added total minus the dropped total (positive when the add outscored
  the drop, negative when the drop outscored the add, "Even" when equal)

#### Scenario: Points window excludes earlier weeks
- **WHEN** an added or dropped player scored in weeks before the transaction's week and in weeks on
  or after it
- **THEN** only the points from the transaction's week onward are counted toward that player's total

#### Scenario: Pure add
- **WHEN** a waiver or free-agent move has an add and no drop
- **THEN** the added player shows their rest-of-season points and no net pickup value is shown

#### Scenario: Pure drop
- **WHEN** a waiver or free-agent move has a drop and no add
- **THEN** the dropped player shows their rest-of-season points and no net pickup value is shown

#### Scenario: Box scores unavailable
- **WHEN** the season's matchup box scores fail to load or do not exist
- **THEN** the waiver or free-agent move renders in its normal form with no points, no net value,
  and no error banner is shown
