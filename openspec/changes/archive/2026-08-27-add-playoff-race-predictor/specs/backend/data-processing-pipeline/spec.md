## MODIFIED Requirements

### Requirement: Write precomputed views per season
For each onboarded season the processor SHALL write `TEAMS`, `MATCHUPS#{season}#WEEK#{week}`, `STANDINGS#{season}`, `WEEKLY_STANDINGS#{season}`, `PLAYOFF_BRACKET#{season}`, `DRAFT#{season}`, and `LEAGUE_SETTINGS#{season}` items matching the DynamoDB schema.

#### Scenario: Full season processed
- **WHEN** the processor runs for an onboarded season
- **THEN** it writes the `TEAMS`, `MATCHUPS`, `STANDINGS`, `WEEKLY_STANDINGS`, `PLAYOFF_BRACKET`, `DRAFT`, and `LEAGUE_SETTINGS` view items for that season

#### Scenario: Idempotent refresh
- **WHEN** the processor re-runs on refresh
- **THEN** existing view items are overwritten in place (idempotent per `(canonical_league_id, SK)`) rather than duplicated

## ADDED Requirements

### Requirement: Persist per-season league settings
The processor SHALL write a `LEAGUE_SETTINGS#{season}` view item carrying `season`, `num_playoff_teams`, `num_playoff_teams_assumed`, `playoff_week_start`, and `regular_season_weeks`, extracted from the platform league-settings payload already stored in S3. When the platform payload omits the playoff-team count, `num_playoff_teams` SHALL default to `6` and `num_playoff_teams_assumed` SHALL be `true`; otherwise `num_playoff_teams_assumed` SHALL be `false`.

#### Scenario: Sleeper settings extracted
- **WHEN** a Sleeper season is processed
- **THEN** `num_playoff_teams` is read from `settings.playoff_teams`, `playoff_week_start` from `settings.playoff_week_start`, and `regular_season_weeks` is `playoff_week_start - 1` (with `playoff_week_start` defaulting to `15` for seasons ≥ 2021 and `14` otherwise when absent)

#### Scenario: ESPN settings extracted
- **WHEN** an ESPN season is processed
- **THEN** `num_playoff_teams` is read from `settings.scheduleSettings.playoffTeamCount`, `regular_season_weeks` from `settings.scheduleSettings.matchupPeriodCount`, and `playoff_week_start` is `matchupPeriodCount + 1`

#### Scenario: Missing playoff-team count defaults
- **WHEN** the platform payload does not provide a playoff-team count
- **THEN** the written `LEAGUE_SETTINGS#{season}` item carries `num_playoff_teams = 6`
