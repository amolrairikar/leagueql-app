## ADDED Requirements

### Requirement: Exclude unplayed matchups from manager history

Per-manager results, high scores, and rivalry accumulators derived from matchups SHALL exclude
unplayed matchups — a matchup whose team scores are both exactly `0`.

#### Scenario: Unplayed matchup excluded from manager history

- **WHEN** a manager's matchups include an unplayed `0-0` week
- **THEN** it does not contribute to that manager's results, high scores, or rivalry totals
