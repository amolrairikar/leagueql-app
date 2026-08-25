## ADDED Requirements

### Requirement: Exclude unplayed matchups from dashboard stats

All-time standings and total-games statistics derived from matchups SHALL exclude unplayed
matchups — a matchup whose team scores are both exactly `0`.

#### Scenario: Unplayed matchup excluded from dashboard

- **WHEN** the matchups include an unplayed `0-0` week
- **THEN** all-time standings (games, wins/losses/ties, points) and the total-games stat count
  played matchups only
