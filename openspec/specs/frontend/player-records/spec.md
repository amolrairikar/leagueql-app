# player-records Specification

## Purpose
The `/player_records` page surfaces all-time fantasy player performance records across the league's history — e.g. the best single-game scoring performances by position — derived from the per-player points recorded in matchup box scores.

## Requirements

### Requirement: List player records by position
`/player_records` SHALL list all-time player performance records by position, each showing player, position, points, and the owner/season context, including only recognized positions.

#### Scenario: Records listed
- **WHEN** the page loads
- **THEN** all-time player performance records are listed by position, each with player, position, points, and owner/season context, limited to recognized positions (`POS_SET`, including D/ST and K)

### Requirement: Exclude unscored rows
Player-rows without a recorded score SHALL be excluded from records.

#### Scenario: Missing points
- **WHEN** a player-row has `points_scored == null`
- **THEN** it is skipped and not counted

### Requirement: Attribute records to the right context
Records SHALL be attributed to the correct team/owner/season of the performance with consistent tie handling.

#### Scenario: Correct attribution
- **WHEN** a player appears on multiple teams/seasons
- **THEN** each record is attributed to the team/owner/season context of that performance, with ties in record values displayed consistently

### Requirement: Exclude unplayed matchups from player leaderboards

Player score leaderboards derived from matchups SHALL exclude unplayed matchups — a matchup whose
team scores are both exactly `0` — so placeholder future weeks never contribute zero-point entries.

#### Scenario: Unplayed matchup excluded from player records

- **WHEN** the matchups include an unplayed `0-0` week
- **THEN** the player score leaderboards (e.g. lowest score) are computed from played matchups only
