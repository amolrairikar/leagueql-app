# sleeper-player-stats-refresher Specification

## Purpose
Scheduled ECS Fargate task that fetches per-player season scoring stats from Sleeper and caches them in S3, where the processing pipeline reads them to compute Sleeper draft analytics (`total_points`, `actual_position_rank`, `draft_rank_delta`, `vorp`). Runs as a Fargate task (no 15-minute Lambda cap) on a weekly schedule, rate-limited to stay within Sleeper's API limits.

## Requirements

### Requirement: Refresh per-player season stats
On a successful run the refresher SHALL write current regular-season stats for available players to `player-stats/sleeper_nfl_player_stats.json`.

#### Scenario: Successful run
- **WHEN** the refresher runs successfully for a season
- **THEN** the S3 stats cache contains current regular-season stats for the available players

#### Scenario: Pipeline can compute draft analytics
- **WHEN** the processing pipeline reads the stats cache
- **THEN** it can compute `total_points`, `vorp`, and position ranks for Sleeper drafts

### Requirement: Deep-merge partial refreshes
A refresh SHALL read the existing cache and deep-merge the freshly fetched `{player_id: {season: stats}}` rather than overwriting, and SHALL bootstrap from empty when no cache exists.

#### Scenario: Merge preserves other seasons and players
- **WHEN** a refresh fetches only the selected players for a single season
- **THEN** previously cached seasons for the same player and players not in this run's selection are preserved

#### Scenario: No existing cache
- **WHEN** the output object does not exist (`NoSuchKey`/`404`)
- **THEN** the run starts from an empty map and writes the fetched stats

### Requirement: Select active players and defenses
The refresher SHALL fetch stats for players with `status == "Active"` plus team defenses via a `position == "DEF"` exception.

#### Scenario: Defenses included
- **WHEN** selecting players to fetch
- **THEN** active players and D/ST (which carry no `status` field) are both fetched, so defenses' draft picks are not left with null `total_points`/position ranks

### Requirement: Resilient, rate-limited fan-out
The refresher SHALL pace requests under the Sleeper rate limit and skip individual player failures without aborting the run.

#### Scenario: Rate limiting
- **WHEN** issuing per-player requests
- **THEN** requests are paced to ~`TARGET_INTERVAL` (≈925 req/min) to avoid 429s

#### Scenario: Per-player failure
- **WHEN** a single player's stats fetch fails
- **THEN** that player is skipped and the run continues

#### Scenario: Full fan-out exceeds 15 minutes
- **WHEN** a full fan-out of thousands of players exceeds 15 minutes
- **THEN** it still completes in a single scheduled Fargate run (no chunking/checkpointing) and writes the canonical cache key

### Requirement: Override env vars for test/on-demand runs
The refresher SHALL support `SEASON`, `MAX_PLAYERS`, and `OUTPUT_KEY` overrides for on-demand and integration-test runs while retaining full production behavior when none are set.

#### Scenario: Bounded test run
- **WHEN** `MAX_PLAYERS` and `OUTPUT_KEY` are set
- **THEN** only the first N active players are processed and results are written to the override key, exercising the full S3-read → live-fetch → S3-write path while leaving the production cache untouched
