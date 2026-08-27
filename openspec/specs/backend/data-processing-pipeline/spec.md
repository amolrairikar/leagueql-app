# data-processing-pipeline Specification

## Purpose
Transform raw platform API payloads stored in S3 into precomputed, query-ready views written to DynamoDB. The processor Lambda runs per-platform DuckDB SQL transforms and writes each view under the league's canonical partition key with an entity-specific sort key. This pipeline backs every read feature; the frontend only ever reads these precomputed items.

## Requirements

### Requirement: Write precomputed views per season
For each onboarded season the processor SHALL write `TEAMS`, `MATCHUPS#{season}#WEEK#{week}`, `STANDINGS#{season}`, `WEEKLY_STANDINGS#{season}`, `PLAYOFF_BRACKET#{season}`, `DRAFT#{season}`, and `LEAGUE_SETTINGS#{season}` items matching the DynamoDB schema.

#### Scenario: Full season processed
- **WHEN** the processor runs for an onboarded season
- **THEN** it writes the `TEAMS`, `MATCHUPS`, `STANDINGS`, `WEEKLY_STANDINGS`, `PLAYOFF_BRACKET`, `DRAFT`, and `LEAGUE_SETTINGS` view items for that season

#### Scenario: Idempotent refresh
- **WHEN** the processor re-runs on refresh
- **THEN** existing view items are overwritten in place (idempotent per `(canonical_league_id, SK)`) rather than duplicated

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

### Requirement: Normalize platform differences
The processor SHALL select per-platform transforms so ESPN and Sleeper inputs produce views with identical schemas.

#### Scenario: Cross-platform schema parity
- **WHEN** ESPN and Sleeper leagues are processed
- **THEN** their resulting views share identical schemas with platform-specific fields (position ID mappings, keeper fields) normalized

#### Scenario: Starter slot labels
- **WHEN** starters are computed
- **THEN** each starter's `fantasy_position` reflects the actual lineup slot filled — Sleeper positionally from `roster_positions`, ESPN from `lineupSlotId` via `ESPN_FANTASY_POSITION_ID_MAPPING` (Superflex/`OP`, `TQB`, flex variants, IDP, `P`, `HC`) — with only slots outside that set falling back to `FLEX`

#### Scenario: Migrated-league owner continuity
- **WHEN** a migrated league is processed
- **THEN** owner IDs are resolved across platforms via the `PLATFORM_MIGRATION` mapping so all-time aggregates stay continuous

### Requirement: Compute draft analytics
The processor SHALL compute `drafted_position_rank`, `actual_position_rank`, `draft_rank_delta`, and `vorp` for draft picks, with `vorp` null for K and D/ST.

#### Scenario: Draft analytics computed
- **WHEN** a `DRAFT#{season}` view is written
- **THEN** each pick carries the computed rank/VORP analytics, with `vorp` null for K and D/ST, and auction fields (`bid_amount`, `nominating_team_id`) populated for auction drafts (null for snake)

### Requirement: Tolerate empty and absent inputs
The processor SHALL write views without erroring when player metadata/stats or a Sleeper bracket are absent, guarding 0-column DuckDB registrations for views that can legitimately be empty.

#### Scenario: Missing player metadata
- **WHEN** `player_name`, `total_points`, or `position` is missing for some players
- **THEN** the affected views are still written with null fields rather than erroring

#### Scenario: Empty bracket season
- **WHEN** a season's Sleeper `playoff_bracket`/`losers_bracket` raw data is empty or absent
- **THEN** no `PLAYOFF_BRACKET#{season}` item is written, its typical-playoff-week matchups are classified `playoff_tier_type = NONE`, and the run does not error

#### Scenario: Empty grouped view guard
- **WHEN** a legitimately-empty view still referenced downstream is registered (`brackets`, `transactions`, `player_scoring_totals`)
- **THEN** it is registered as a typed 0-row frame (numeric columns kept numeric) so DuckDB does not crash, and the `DRAFT` (SLEEPER) transform binds against an empty `player_scoring_totals` to yield draft rows with no scoring/VORP for that season

#### Scenario: Other empty view attribution
- **WHEN** any other view is unexpectedly empty at registration
- **THEN** it is logged by name before the failing registration so it is attributable from the logs

### Requirement: Reconstruct partial Sleeper bracket links
The processor SHALL reconstruct missing Sleeper `t1_from`/`t2_from` feeder links from round and winner/loser membership so bracket tiering is identified correctly.

#### Scenario: Feeder links only on the final round
- **WHEN** a Sleeper winners bracket populates `from` links only on the final round
- **THEN** the processor reconstructs the missing links from prior-round membership so `WINNERS_BRACKET` vs `WINNERS_CONSOLATION_LADDER` tiering is correct, preserving links Sleeper already provided and keeping a bye team's `from` null

### Requirement: Select seasons to process
The processor SHALL recompute only the latest season on a normal refresh, and every season in the manifest when `reprocess_all=true`.

#### Scenario: Normal refresh
- **WHEN** a normal refresh runs
- **THEN** only the latest season is recomputed (`resolve_seasons_to_process`)

#### Scenario: Reprocess all
- **WHEN** the manifest carries `reprocess_all=true`
- **THEN** the processor recomputes every season in the manifest from the raw season files already in S3

### Requirement: Fail cleanly on processing errors
A processing failure SHALL write a `FAILED` job status and SHALL NOT leave partially-valid `METADATA` marked as completed.

#### Scenario: Processing failure
- **WHEN** processing fails
- **THEN** a `FAILED` job status is written and `METADATA` is not marked completed with partial data

### Requirement: Exclude unplayed matchups from standings

The processor SHALL treat a regular-season matchup whose team scores are both exactly `0` as
unplayed and exclude it from the `STANDINGS` and `WEEKLY_STANDINGS` view computations, while still
writing that matchup into the `MATCHUPS#{season}#WEEK#{week}` view. Wins, losses, ties, win
percentage, points for/against (and their averages), games played, and the per-week all-play
("vs league") ranking SHALL reflect only played matchups.

#### Scenario: Unplayed week excluded from standings

- **WHEN** a season contains a regular-season week whose matchups are all `0-0` (unplayed)
- **THEN** `STANDINGS#{season}` and `WEEKLY_STANDINGS#{season}` do not count that week — games
  played, wins/losses/ties, win %, and points for/against are computed from the played weeks only

#### Scenario: Unplayed matchup still stored

- **WHEN** an unplayed `0-0` week is processed
- **THEN** its `MATCHUPS#{season}#WEEK#{week}` item is still written with the `0-0` rows intact

#### Scenario: Genuine played game with a zero score is retained

- **WHEN** a played matchup has one team scoring `0` and the other scoring more than `0`
- **THEN** it is counted in standings as a normal decided game (not excluded)
