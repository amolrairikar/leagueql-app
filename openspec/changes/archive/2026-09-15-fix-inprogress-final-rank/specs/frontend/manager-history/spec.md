## ADDED Requirements

### Requirement: Show current standings position for an in-progress season

For a season with no finalized placement — a `final_rank` that is `0` (as ESPN reports
`rankCalculatedFinal` before a season is finalized) or absent — with at least one game
played, the per-season finish SHALL show the manager's current standings position
(derived from the regular-season record, ordered by wins then points-for) rather than a
rank of `0`. A champion or runner-up still resolves to a finish of 1st or 2nd; a season
with no games played yet shows no finish ("—").

#### Scenario: In-progress season shows current standings position

- **WHEN** a selected manager has an in-progress season whose row carries `final_rank: 0`
  and at least one played game
- **THEN** that season's finish renders as the manager's current standings position
  (ordered by wins, then points-for), not "0th place"
