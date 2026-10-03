## MODIFIED Requirements

### Requirement: Derive playoff appearances and championships
Playoff appearances SHALL be derived from the winners' bracket, and championships SHALL be counted from the seasons in which the manager's team carries the STANDINGS `champion = Yes` flag, with identities correct across migrated platforms.

#### Scenario: Playoff/championship derivation
- **WHEN** two managers are compared
- **THEN** playoff appearances (distinct seasons reaching the winners' bracket) and championships (seasons whose STANDINGS row has `champion = Yes`) are derived, with owner identities remapped across platforms

#### Scenario: Championship in a league whose final is not week 17
- **WHEN** a compared manager's team won a title game played in matchup period 15 and is marked
  `champion = Yes` in that season's standings
- **THEN** that season counts as one championship for the manager
