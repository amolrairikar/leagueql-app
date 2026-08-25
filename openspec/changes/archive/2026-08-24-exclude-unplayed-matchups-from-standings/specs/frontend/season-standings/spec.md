## ADDED Requirements

### Requirement: Exclude unplayed matchups from client-side computations

Strength-of-schedule and expected-wins SHALL exclude unplayed matchups — a matchup whose team
scores are both exactly `0` — so future/placeholder weeks add no phantom opponents or simulated
games.

#### Scenario: Unplayed matchup excluded from SoS and expected wins

- **WHEN** the selected season's matchups include an unplayed `0-0` week
- **THEN** strength-of-schedule and expected-wins are computed from played matchups only, and the
  unplayed opponents are not added to any team's schedule
