## MODIFIED Requirements

### Requirement: Persist per-season league settings
The processor SHALL write a `LEAGUE_SETTINGS#{season}` view item carrying `season`, `num_playoff_teams`, `num_playoff_teams_assumed`, `playoff_week_start`, and `regular_season_weeks`, extracted from the platform league-settings payload already stored in S3. When the platform payload omits the playoff-team count, `num_playoff_teams` SHALL default to `6` and `num_playoff_teams_assumed` SHALL be `true`; otherwise `num_playoff_teams_assumed` SHALL be `false`.

#### Scenario: Sleeper settings extracted
- **WHEN** a Sleeper season is processed
- **THEN** `num_playoff_teams` is the league's playoff-team count, `playoff_week_start` is the league's first playoff week, and `regular_season_weeks` is `playoff_week_start - 1` (with `playoff_week_start` defaulting to `15` for seasons ≥ 2021 and `14` otherwise when the league does not provide it)

#### Scenario: ESPN settings extracted
- **WHEN** an ESPN season is processed
- **THEN** `num_playoff_teams` is the league's playoff-team count, `regular_season_weeks` is the league's number of regular-season matchup weeks, and `playoff_week_start` is `regular_season_weeks + 1`

#### Scenario: Yahoo settings extracted
- **WHEN** a Yahoo season is processed
- **THEN** `num_playoff_teams` is the league's playoff-team count, `playoff_week_start` is the
  league's first playoff week, and `regular_season_weeks` is `playoff_week_start - 1`

#### Scenario: Missing playoff-team count defaults
- **WHEN** the platform payload does not provide a playoff-team count
- **THEN** the written `LEAGUE_SETTINGS#{season}` item carries `num_playoff_teams = 6`

### Requirement: Derive the Yahoo playoff bracket from playoff-week matchups
Because the Yahoo API exposes no standalone bracket resource, the processor SHALL derive a Yahoo
season's `PLAYOFF_BRACKET#{season}` view from the playoff-week matchups, producing the same
bracket schema (rounds, match links, winners/losers, final positions, bracket type) as the ESPN
and Sleeper transforms. Playoff games SHALL be tiered by bracket path: a playoff game between two
teams that have not yet lost a playoff game is a winners-bracket game; a playoff game involving a
team already eliminated from title contention is a placement (winners-consolation) game; and a
consolation-bracket game between teams that missed the playoffs is a losers-tier game that is
excluded from the bracket view.

#### Scenario: Bracket derived from playoff weeks
- **WHEN** a Yahoo season with completed playoff-week matchups is processed
- **THEN** a `PLAYOFF_BRACKET#{season}` view is written whose schema matches the ESPN/Sleeper
  bracket views, with rounds and championship/consolation tiering inferred from the playoff-week
  matchups

#### Scenario: Placement game is not a championship game
- **WHEN** a Yahoo season's final playoff week contains both the title game and a 3rd-place game
  between the two semifinal losers
- **THEN** only the title game is a winners-bracket game with bracket position 1, and the
  3rd-place game is a placement game

#### Scenario: Consolation bracket excluded
- **WHEN** a Yahoo season has consolation-bracket games between teams that missed the playoffs
- **THEN** those games are losers-tier matchups and do not appear in the `PLAYOFF_BRACKET#{season}`
  view

#### Scenario: No playoff matchups yet
- **WHEN** a Yahoo season has no completed playoff-week matchups
- **THEN** no `PLAYOFF_BRACKET#{season}` item is written and the run does not error

## ADDED Requirements

### Requirement: Determine a single champion per season
The STANDINGS view SHALL mark as champion the winner of the winners-bracket game in each season's
last winners-bracket week, for every platform.

#### Scenario: Exactly one champion
- **WHEN** a season with a completed winners bracket is processed
- **THEN** exactly one team in that season's standings has `champion = Yes`

#### Scenario: Playoffs ending before week 17
- **WHEN** a season's title game is played before week 17
- **THEN** that game's winner is marked as the season's champion
