# Spec Delta

## ADDED Requirements

### Requirement: Omit the playoff-result pill for an in-progress season

A season card SHALL show the playoff-result pill ("Champion", "Runner-up", "Playoffs", or
"Missed Playoffs") only for a finalized season, meaning at least one team has a `final_rank`
≥ 1. For an in-progress season, the card SHALL omit the pill while still showing the season's
record, points, and current finish.

#### Scenario: In-progress season has no result pill

- **WHEN** a selected manager has an in-progress season where no team has a finalized
  `final_rank`
- **THEN** that season's card shows no "Champion", "Runner-up", "Playoffs", or
  "Missed Playoffs" pill

#### Scenario: Finalized season keeps its result pill

- **WHEN** a selected manager has a finalized season in which they won the championship
- **THEN** that season's card shows the "Champion" pill
