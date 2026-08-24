# season-standings Specification

## Purpose
The `/standings` page shows final standings for a selected season plus season superlative awards. Standings include record, win %, points for/against, vs-league record, an expected-wins figure, and a strength-of-schedule (SoS) rating, both derived client-side from the season's `MATCHUPS`. A season selector switches between onboarded seasons. The page also hosts the Schedule-Swap Simulator scoped to the same selector.

## Requirements

### Requirement: Show season standings
`/standings` SHALL show the selected season's standings — record, win %, PF, PA, vs-league record, expected wins, SoS — sorted by standing, correctly accounting for ties.

#### Scenario: Standings table
- **WHEN** a season is selected
- **THEN** the table shows record, win %, PF, PA, vs-league record, expected wins, and SoS, sorted by standing, with `W-L-T` ties reflected in the record and win %

### Requirement: Compute expected wins
Expected wins SHALL show each team's average wins across every schedule (the mean of its schedule-swap row), or `—` when it cannot be computed.

#### Scenario: Expected wins value
- **WHEN** the season's matchups are available
- **THEN** expected wins shows each team's mean win total across all managers' schedules

#### Scenario: Expected wins unavailable
- **WHEN** matchups are unavailable or a team has no simulated regular-season games
- **THEN** expected wins shows `—`

### Requirement: Compute strength of schedule
SoS SHALL show each team's average opponent season win % over the regular season, or `—` when it cannot be computed.

#### Scenario: SoS value
- **WHEN** the season's matchups and opponents' win % are available
- **THEN** SoS shows each team's average opponent season win % (playoff games excluded)

#### Scenario: SoS unavailable
- **WHEN** a team has no regular-season opponents or the matchups query fails
- **THEN** SoS (and expected wins) show `—` and the table still renders

### Requirement: Season selection and awards
The season selector SHALL list all onboarded seasons and default to the latest, and season superlative awards SHALL be shown for the selected season, rendering in-progress seasons without error.

#### Scenario: Selector default
- **WHEN** the page loads
- **THEN** the selector lists all onboarded seasons and defaults to the most recent

#### Scenario: Awards and in-progress
- **WHEN** a season is selected (including an in-progress one)
- **THEN** its superlative awards are displayed and the page renders without error

### Requirement: Distinguish missing season champion
The Season Champion card SHALL show "TBD"/"Season in progress" only for the latest season with no champion, and "N/A"/"No champion" for a completed earlier season.

#### Scenario: Champion card labels
- **WHEN** the selected season has no recorded champion
- **THEN** the latest season shows "TBD"/"Season in progress" and an earlier completed season shows "N/A"/"No champion"
