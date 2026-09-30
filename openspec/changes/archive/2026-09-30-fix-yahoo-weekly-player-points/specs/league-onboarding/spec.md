## ADDED Requirements

### Requirement: Fetch Yahoo weekly rosters with player points per team
Onboarding or refreshing a Yahoo league SHALL fetch each team's roster and weekly player points
separately for every fetched week of every onboarded season, and SHALL store them as a single
weekly roster record per season and week. This is needed because the league-wide roster request
does not return player points.

#### Scenario: Weekly player points populated
- **WHEN** a Yahoo league is onboarded or refreshed and a fetched week has been played
- **THEN** every rostered player in that week's roster record has their weekly points, with the
  lineup slot they were in, and each team's starter points add up to that team's matchup score

#### Scenario: One roster record per week
- **WHEN** the rosters for every team in a season/week have been fetched
- **THEN** they are stored as one weekly roster record that contains every team's players

#### Scenario: Unknown team count
- **WHEN** a season's team count cannot be determined from the league metadata
- **THEN** that season's weekly rosters are not fetched, and its matchups are still onboarded
  with empty lineups
