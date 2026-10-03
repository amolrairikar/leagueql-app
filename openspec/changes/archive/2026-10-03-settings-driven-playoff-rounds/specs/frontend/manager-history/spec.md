## ADDED Requirements

### Requirement: Identify the runner-up from the title game
For a finalized season, a manager SHALL be the runner-up when their team lost the season's decided
winners-bracket matchup labeled "Finals", in whatever week that game was played.

#### Scenario: Runner-up of an early final
- **WHEN** a manager's team lost a finalized season's "Finals" winners-bracket game played in
  matchup period 15
- **THEN** that season's card shows the "Runner-up" pill and a 2nd-place finish when no
  `final_rank` is available
