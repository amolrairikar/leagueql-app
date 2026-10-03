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

### Requirement: Compute draft analytics
The processor SHALL compute `drafted_position_rank`, `actual_position_rank`, `draft_rank_delta`, and `vorp` for draft picks, with `vorp` null for K and D/ST.

#### Scenario: Draft analytics computed
- **WHEN** a `DRAFT#{season}` view is written
- **THEN** each pick carries the computed rank/VORP analytics, with `vorp` null for K and D/ST, and auction fields (`bid_amount`, `nominating_team_id`) populated for auction drafts (null for snake)

### Requirement: Tolerate empty and absent inputs
The processor SHALL write views without erroring when player metadata/stats or a Sleeper bracket are absent, when a Sleeper matchup entry's lineup fields (`starters`, `starters_points`, `players`, `players_points`) are null rather than merely omitted, guarding 0-column DuckDB registrations for views that can legitimately be empty.

#### Scenario: Missing player metadata
- **WHEN** `player_name`, `total_points`, or `position` is missing for some players
- **THEN** the affected views are still written with null fields rather than erroring

#### Scenario: Null Sleeper matchup lineup fields
- **WHEN** a Sleeper matchup entry carries a null value for `starters`, `starters_points`, `players`, or `players_points` (e.g. a team with no lineup set that week)
- **THEN** that team contributes no starter/bench stat rows for the matchup and the run completes without erroring, the same as when the field is absent or empty

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
The processor SHALL recompute only the latest season on a normal refresh, every season in the manifest when `reprocess_all=true`, and exactly the listed seasons when the manifest carries `reprocess_seasons`. These flags, the job's `correlation_id`, and the previous manifest used for the normal-refresh diff SHALL come from the manifest version that triggered the run, not from whichever version is newest when the run reads it.

#### Scenario: Normal refresh
- **WHEN** a normal refresh runs
- **THEN** only the latest season is recomputed (`resolve_seasons_to_process`)

#### Scenario: Reprocess all
- **WHEN** the manifest carries `reprocess_all=true`
- **THEN** the processor recomputes every season in the manifest from the raw season files already in S3

#### Scenario: Reprocess specific seasons
- **WHEN** the manifest carries `reprocess_seasons=2019`
- **THEN** the processor recomputes only season 2019 from the raw season files already in S3,
  regardless of the previous manifest's seasons

#### Scenario: Manifest overwritten before the run reads it
- **WHEN** a backfill writes the manifest with `reprocess_all=true` and, before the processor run it
  triggered reads the manifest, the lineup backfill copies it with `reprocess_seasons=2026`
- **THEN** the backfill's run still recomputes every season and records the backfill's
  `correlation_id`, and the lineup backfill's own run recomputes only 2026

#### Scenario: Previous manifest is relative to the triggering version
- **WHEN** a run is triggered by a manifest version that is no longer the newest
- **THEN** the previous manifest used for the season diff is the version written immediately before
  the triggering one

#### Scenario: Event without a version id
- **WHEN** the triggering S3 event carries no `versionId`
- **THEN** the processor reads the current manifest and uses the second-newest version as the
  previous manifest

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

### Requirement: Determine a single champion per season
The STANDINGS view SHALL mark as champion the winner of the winners-bracket game in each season's
last winners-bracket week, for every platform.

#### Scenario: Exactly one champion
- **WHEN** a season with a completed winners bracket is processed
- **THEN** exactly one team in that season's standings has `champion = Yes`

#### Scenario: Playoffs ending before week 17
- **WHEN** a season's title game is played before week 17
- **THEN** that game's winner is marked as the season's champion

### Requirement: Merge backfilled Yahoo lineups into matchups
When processing a Yahoo season, the processor SHALL attach starter and bench lineups to each
matchup from the season's backfilled lineup store when one exists. Stored lineups SHALL take
precedence over any weekly rosters carried in the raw season file. Without either, the season's
matchups SHALL have empty lineups.

#### Scenario: Backfilled lineups attached
- **WHEN** a Yahoo season with a lineup store for weeks 1–14 is processed
- **THEN** each matchup in weeks 1–14 has starter and bench lineups with each player's weekly
  points, and each team's starter points add up to its matchup score

#### Scenario: Legacy in-file rosters still used
- **WHEN** a Yahoo season has weekly rosters in its raw season file and no lineup store
- **THEN** its matchups get lineups from the in-file rosters

#### Scenario: No lineups yet
- **WHEN** a Yahoo season has neither a lineup store nor in-file rosters
- **THEN** its matchups are written with empty starter and bench lineups and every other view is
  unaffected

### Requirement: Resolve stable Yahoo owner identities across seasons
The processor SHALL assign each person in a Yahoo league one owner id used in every season they
appear in, linking teams across seasons by real guid, then manager nickname, then team name, then
custom (non-default) team logo. A link SHALL be made only when exactly one earlier identity
matches and that identity is not already linked to another team in the same season. The owner id
SHALL be the person's real guid when known, otherwise the team key from their first season.

#### Scenario: Manager moves to a different slot
- **WHEN** a manager with nickname "Manager A" owns slot 10 in one season and slot 9 in the next
- **THEN** both seasons' teams carry the same owner id, and the manager who takes over slot 10
  gets a different owner id

#### Scenario: Title credited to the real winner
- **WHEN** "Manager B" wins a season in slot 12, leaves, and "Manager C" later takes slot 12 and
  wins another season
- **THEN** the standings mark each title under a different owner id, so each manager is credited
  with exactly one title

#### Scenario: Returning manager after a gap
- **WHEN** a manager plays one season, sits out one or more seasons, and then returns in another slot
- **THEN** the returning team is linked to the manager's earlier owner id

#### Scenario: Real guid takes precedence
- **WHEN** a team has a real guid that matches an earlier identity
- **THEN** it is linked by guid, even if its nickname or team name changed

#### Scenario: Masked or ambiguous nicknames never merge
- **WHEN** a manager's nickname is `--hidden--`, or two teams in the same season share a nickname
- **THEN** no link is made by nickname for those teams, and they are linked only by guid, team
  name, or custom logo, or else become new identities

#### Scenario: Team name or custom logo links a renamed manager
- **WHEN** a manager's nickname changes between seasons but their team name or custom logo URL is
  unchanged
- **THEN** the team is linked to the manager's earlier owner id

#### Scenario: Default logos are not used to link
- **WHEN** two teams in different seasons share a Yahoo default logo URL and nothing else
- **THEN** they are not linked

#### Scenario: New manager
- **WHEN** a team matches no earlier identity by any signal
- **THEN** it gets a new owner id equal to its own team key, or its real guid when it has one

#### Scenario: Legacy raw data without separate guid fields
- **WHEN** a raw Yahoo season file predates the separate `guid`/`slot_manager_id` fields
- **THEN** a non-numeric `manager_id` is treated as a real guid, and a numeric one is treated as
  a slot number to be linked by nickname, team name, and logo

### Requirement: Keep Yahoo owner ids consistent across incremental refreshes
When processing only some seasons of a Yahoo league, the processor SHALL resolve owner identities
using the team data of every season in the league, so owner ids written for seasons not being
reprocessed remain valid.

#### Scenario: Latest-season refresh keeps earlier ids
- **WHEN** a Yahoo league that was fully processed is refreshed and only its latest season is
  reprocessed
- **THEN** every manager's owner id in the reprocessed season equals the owner id already stored
  for that manager in earlier seasons

#### Scenario: New season appended
- **WHEN** a new Yahoo season is added and processed on its own
- **THEN** returning managers keep their existing owner ids and only new managers get new ids

### Requirement: Translate Yahoo migration mappings to stable owner ids
When a league migrated to Yahoo has a `PLATFORM_MIGRATION` mapping that has not yet been
translated, the processor SHALL rewrite each destination owner id from the id the Yahoo members
proxy returned to that manager's stable owner id, and SHALL mark the mapping as translated so it
is rewritten only once.

#### Scenario: Mapping translated on first processing
- **WHEN** a league migrated from another platform to Yahoo is processed for the first time
- **THEN** each mapping entry's destination owner id becomes the stable owner id of the Yahoo team
  that id identified in the latest season, entries marked `__not_returning__` are unchanged, and
  the mapping is flagged as translated

#### Scenario: Already-translated mapping left alone
- **WHEN** a Yahoo league whose mapping is already flagged as translated is processed again
- **THEN** the mapping is not modified
