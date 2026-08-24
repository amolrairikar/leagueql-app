# manager-history Specification

## Purpose
The `/manager_history` page shows the year-to-year performance arc of each manager: per-season records and finishes, plus a rivalry tracker that classifies each opponent relationship as a domination, nemesis, or even rivalry based on head-to-head win rate.

## Requirements

### Requirement: Show per-season history
`/manager_history` SHALL show the selected manager's per-season records and finishes, including postseason games, with identities correct across migrated platforms, and render for a manager with only one season.

#### Scenario: Per-season records
- **WHEN** a manager is selected
- **THEN** their per-season records and finishes are shown, built from schedules that include winners/losers/consolation postseason games, with owner identities remapped across platforms

#### Scenario: Single-season manager
- **WHEN** the selected manager has only one season of history
- **THEN** the history renders with the limited data

### Requirement: Classify rivalries by win rate
The rivalry tracker SHALL classify opponents as domination (win rate ≥ 0.65), nemesis (< 0.40), or even, handling small samples so a single game is not misleading.

#### Scenario: Rivalry classification
- **WHEN** head-to-head win rates against opponents are computed
- **THEN** each opponent is classified domination / nemesis / even using the thresholds, with small-sample rivalries handled so a 1-game "rivalry" is not misleading
