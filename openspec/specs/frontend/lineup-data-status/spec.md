# frontend/lineup-data-status Specification

## Purpose
Tell users when a league's weekly player scores are still loading or couldn't be loaded, and keep
lineup-dependent features from showing misleading zero-point lineups for those seasons.

## Requirements

### Requirement: Notification bell for pending player scores
The app header SHALL show a notification bell with an indicator when the current league has any
pending or failed lineup seasons (from `GET /leagues/{leagueId}`). Opening it SHALL list those
seasons with a short explanation. The bell SHALL be hidden when there are none, in demo mode, and
when no league is connected.

#### Scenario: Seasons still loading
- **WHEN** the league has pending lineup seasons 2019–2024
- **THEN** the bell shows an indicator, and opening it says player box scores for 2019–2024 are
  still loading

#### Scenario: Season failed
- **WHEN** the league has failed lineup season 2019
- **THEN** opening the bell says player scores for 2019 couldn't be loaded yet and will be retried
  automatically

#### Scenario: Nothing pending
- **WHEN** both lists are empty, or the metadata request fails
- **THEN** no bell is shown

### Requirement: Pending state in box scores
A box score for a matchup in a pending or failed lineup season SHALL show a "player scores still
loading" placeholder instead of player rows. Team scores SHALL still be shown.

#### Scenario: Pending season box score
- **WHEN** the user opens a 2020 box score while 2020 is lineup-pending
- **THEN** both team scores are shown with a "player scores still loading" placeholder and no
  zero-point player rows

#### Scenario: Backfilled season box score
- **WHEN** the user opens a box score for a season that is not pending or failed
- **THEN** the starter and bench player rows are shown as before

### Requirement: Exclude pending seasons from lineup-derived stats
Lineup efficiency, player records, matchup records, manager history, manager comparison, playoff
bracket box scores, and matchup previews SHALL leave pending or failed lineup seasons out of any
statistic computed from player lineups. They SHALL show an inline note naming the excluded seasons.

#### Scenario: Lineup efficiency excludes pending season
- **WHEN** lineup efficiency is viewed while 2020 is lineup-pending
- **THEN** 2020 contributes no lineup-efficiency values and an inline note says 2020's player
  scores are still loading

#### Scenario: No pending seasons
- **WHEN** no seasons are pending or failed
- **THEN** these features show no note and include every season as before
