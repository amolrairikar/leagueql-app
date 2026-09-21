## MODIFIED Requirements

### Requirement: Normalize platform differences
The processor SHALL select per-platform transforms so ESPN, Sleeper, and Yahoo inputs produce
views with identical schemas.

#### Scenario: Cross-platform schema parity
- **WHEN** ESPN, Sleeper, and Yahoo leagues are processed
- **THEN** their resulting views share identical schemas with platform-specific fields (position
  mappings, keeper fields) normalized

#### Scenario: Starter slot labels
- **WHEN** starters are computed
- **THEN** each starter's `fantasy_position` reflects the actual lineup slot filled — Sleeper
  positionally from `roster_positions`, ESPN from `lineupSlotId` via
  `ESPN_FANTASY_POSITION_ID_MAPPING` (Superflex/`OP`, `TQB`, flex variants, IDP, `P`, `HC`), and
  Yahoo from its `selected_position` — with only slots outside the known set falling back to `FLEX`

#### Scenario: Migrated-league owner continuity
- **WHEN** a migrated league is processed
- **THEN** owner IDs are resolved across platforms via the `PLATFORM_MIGRATION` mapping so all-time
  aggregates stay continuous

#### Scenario: Yahoo team without a resolvable manager still appears
- **WHEN** a Yahoo team has no matching member (Yahoo exposed no manager, or the manager parsed to
  a null owner id)
- **THEN** the team still appears in the `TEAMS` view (owner display fields null) rather than being
  dropped, so the dependent matchups, standings, playoff bracket, and draft views are still
  populated

### Requirement: Persist per-season league settings
The processor SHALL write a `LEAGUE_SETTINGS#{season}` view item carrying `season`,
`num_playoff_teams`, `num_playoff_teams_assumed`, `playoff_week_start`, and `regular_season_weeks`,
extracted from the platform league-settings payload already stored in S3. When the platform payload
omits the playoff-team count, `num_playoff_teams` SHALL default to `6` and
`num_playoff_teams_assumed` SHALL be `true`; otherwise `num_playoff_teams_assumed` SHALL be `false`.

#### Scenario: Sleeper settings extracted
- **WHEN** a Sleeper season is processed
- **THEN** `num_playoff_teams` is read from `settings.playoff_teams`, `playoff_week_start` from
  `settings.playoff_week_start`, and `regular_season_weeks` is `playoff_week_start - 1` (with
  `playoff_week_start` defaulting to `15` for seasons ≥ 2021 and `14` otherwise when absent)

#### Scenario: ESPN settings extracted
- **WHEN** an ESPN season is processed
- **THEN** `num_playoff_teams` is read from `settings.scheduleSettings.playoffTeamCount`,
  `regular_season_weeks` from `settings.scheduleSettings.matchupPeriodCount`, and
  `playoff_week_start` is `matchupPeriodCount + 1`

#### Scenario: Yahoo settings extracted
- **WHEN** a Yahoo season is processed
- **THEN** `num_playoff_teams` is read from the Yahoo settings `num_playoff_teams`,
  `playoff_week_start` from `playoff_start_week`, and `regular_season_weeks` is
  `playoff_start_week - 1`

#### Scenario: Missing playoff-team count defaults
- **WHEN** the platform payload does not provide a playoff-team count
- **THEN** the written `LEAGUE_SETTINGS#{season}` item carries `num_playoff_teams = 6`

## ADDED Requirements

### Requirement: Derive the Yahoo playoff bracket from playoff-week matchups
Because the Yahoo API exposes no standalone bracket resource, the processor SHALL derive a Yahoo
season's `PLAYOFF_BRACKET#{season}` view from the scoreboard matchups flagged as playoff games,
producing the same bracket schema (rounds, match links, winners/losers, final positions, bracket
type) as the ESPN and Sleeper transforms.

#### Scenario: Bracket derived from playoff weeks
- **WHEN** a Yahoo season with completed playoff-week matchups is processed
- **THEN** a `PLAYOFF_BRACKET#{season}` view is written whose schema matches the ESPN/Sleeper
  bracket views, with rounds and championship/consolation tiering inferred from the playoff-week
  matchups

#### Scenario: No playoff matchups yet
- **WHEN** a Yahoo season has no completed playoff-week matchups
- **THEN** no `PLAYOFF_BRACKET#{season}` item is written and the run does not error

### Requirement: Resolve Yahoo players from the player-data cache
Because the per-league Yahoo payloads carry player *keys* (not names or season points), the
processor SHALL resolve Yahoo player names/positions from `player-metadata/yahoo_nfl_players.json`
and season scoring from `player-stats/yahoo_nfl_player_stats.json` in S3 (as it does for Sleeper),
and SHALL tolerate a missing cache without failing the run.

#### Scenario: Names and scoring resolved from cache
- **WHEN** a Yahoo league is processed and the Yahoo player-data caches are present
- **THEN** draft and transaction player keys are resolved to names/positions and draft analytics
  (`total_points`, `vorp`, position ranks) are computed from the cached season scoring

#### Scenario: Missing Yahoo player-data cache
- **WHEN** the Yahoo player metadata or stats cache is absent from S3
- **THEN** the affected views are still written with null player names/scoring rather than erroring
