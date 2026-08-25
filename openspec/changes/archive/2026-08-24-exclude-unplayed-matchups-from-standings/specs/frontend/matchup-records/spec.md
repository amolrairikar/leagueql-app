## ADDED Requirements

### Requirement: Exclude unplayed matchups from record leaderboards

Matchup and score record leaderboards SHALL exclude unplayed matchups — a matchup whose team
scores are both exactly `0` — so placeholder future games never appear as records.

#### Scenario: Unplayed matchup excluded from records

- **WHEN** the matchups include an unplayed `0-0` week
- **THEN** the lowest-score, closest-game, and other matchup record leaderboards are computed from
  played matchups only and never surface a `0-0` placeholder
