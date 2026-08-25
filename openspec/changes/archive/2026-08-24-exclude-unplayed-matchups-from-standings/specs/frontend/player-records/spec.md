## ADDED Requirements

### Requirement: Exclude unplayed matchups from player leaderboards

Player score leaderboards derived from matchups SHALL exclude unplayed matchups — a matchup whose
team scores are both exactly `0` — so placeholder future weeks never contribute zero-point entries.

#### Scenario: Unplayed matchup excluded from player records

- **WHEN** the matchups include an unplayed `0-0` week
- **THEN** the player score leaderboards (e.g. lowest score) are computed from played matchups only
