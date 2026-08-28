# transactions Specification

## ADDED Requirements

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
