## ADDED Requirements

### Requirement: Exclude unplayed matchups from simulation

The schedule-swap simulation SHALL exclude unplayed matchups — a matchup whose team scores are
both exactly `0` — so simulated records replay only played weeks.

#### Scenario: Unplayed matchup excluded from simulation

- **WHEN** the season's matchups include an unplayed `0-0` week
- **THEN** the simulated records for every schedule are computed from played weeks only
