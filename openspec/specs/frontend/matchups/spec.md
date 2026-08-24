# matchups Specification

## Purpose
The `/matchups` page browses every historical matchup. The user selects a season and week to see all matchups for that week, and can open a matchup to view the full box score (starters and bench with per-player points) for both teams. It also hosts the Weekly Awards & Superlatives section below the matchup grid.

## Requirements

### Requirement: Browse matchups by season and week
`/matchups` SHALL let the user pick a season and week and list all matchups for that week with team names, logos, scores, and winner, offering only weeks that exist for the chosen season.

#### Scenario: Week matchup list
- **WHEN** the user selects a season and week
- **THEN** all matchups for that week are listed with team names, logos, scores, and the winner

#### Scenario: Week selector bounds
- **WHEN** the week selector is populated for a season
- **THEN** it offers only weeks that exist for that season

### Requirement: Open a box score
Opening a matchup SHALL show both teams' starters and bench with per-player points.

#### Scenario: Box score
- **WHEN** the user opens a matchup
- **THEN** both teams' starters and bench are shown with per-player points

### Requirement: Label playoff matchups
Playoff matchups SHALL display their round label.

#### Scenario: Playoff round label
- **WHEN** a matchup carries `playoff_tier_type`/`playoff_round`
- **THEN** the postseason round label is displayed

### Requirement: Render sparse/in-progress data gracefully
The page SHALL render byes, in-progress weeks, and missing player metadata without error.

#### Scenario: Graceful rendering
- **WHEN** a week has a bye/odd team count, incomplete/zero in-progress scores, or missing player names/positions
- **THEN** the matchup grid and box score render gracefully (falling back to avatars for missing logos)
