# player-metadata-refresher Specification

## Purpose
Scheduled Lambda that keeps the Sleeper NFL player-metadata cache fresh. It fetches the full Sleeper players list and stores it in S3, where the processing pipeline reads it to resolve `player_id` → name/position for draft and matchup views, decoupling per-league processing from the large, slow-changing Sleeper players endpoint.

## Requirements

### Requirement: Refresh the player-metadata cache
On a successful run the refresher SHALL write the latest Sleeper players list to the S3 cache key (`player-metadata/sleeper_nfl_players.json` by default, overridable via `PLAYER_METADATA_S3_KEY`).

#### Scenario: Successful refresh
- **WHEN** the refresher runs successfully
- **THEN** the S3 player-metadata cache reflects the latest Sleeper players list

#### Scenario: Pipeline can resolve players
- **WHEN** the processing pipeline reads the cache
- **THEN** it can resolve Sleeper `player_id`s to name/position

### Requirement: Preserve the cache on failure
The refresher SHALL NOT overwrite the existing cache with bad or partial data, and SHALL treat NFL state as advisory.

#### Scenario: Failed fetch
- **WHEN** the players endpoint fails or returns a partial payload
- **THEN** the previous S3 cache is left intact

#### Scenario: NFL state fetch fails
- **WHEN** the NFL state fetch fails
- **THEN** the run logs a warning and continues

### Requirement: Handle players missing required fields
The refresher SHALL handle players lacking `first_name`, `last_name`, or `position` without corrupting the cache.

#### Scenario: Incomplete player records
- **WHEN** some players lack required fields
- **THEN** they are filtered/handled so downstream lookups stay valid and the cache is not corrupted
