## ADDED Requirements

### Requirement: Exclude unplayed matchups from head-to-head stats

Head-to-head records, win percentages, average points, and the game log SHALL exclude unplayed
matchups — a matchup whose team scores are both exactly `0` — so future placeholder games are not
counted as ties or listed in the log.

#### Scenario: Unplayed matchup excluded from comparison

- **WHEN** two managers have an unplayed `0-0` matchup scheduled
- **THEN** it is not counted in their records/win% and does not appear in the head-to-head game log
