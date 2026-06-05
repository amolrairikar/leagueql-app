# BE-010: Player Metadata Refresher

## Description
Scheduled Lambda that keeps the Sleeper NFL player metadata cache fresh. Fetches the full
Sleeper players list and stores it in S3, where the processing pipeline reads it to resolve
`player_id` → name/position for draft and matchup views. Decouples per-league processing
from the large, slow-changing Sleeper players endpoint.

## Scope
- Lambda: `src/player_metadata/` (`handler.py`, `utils.py`).
- Source: `https://api.sleeper.app/v1/players/nfl`; NFL state from
  `https://api.sleeper.app/v1/state/nfl`.
- Output: S3 key `player-metadata/sleeper_nfl_players.json` (default; overridable via the
  `PLAYER_METADATA_S3_KEY` env var so integration tests can write outside the bucket
  notification filter and avoid triggering [BE-011](BE-011-sleeper-player-stats-refresher.md)).
- Required fields per player: `first_name`, `last_name`, `position`.

## Edge Cases
- **NFL state fetch fails:** log a warning and continue (state is advisory).
- **Players endpoint fails / partial payload:** do not overwrite the existing S3 cache with
  bad data.
- **Players missing required fields:** filtered/handled so downstream lookups stay valid.
- **Large payload:** the Sleeper players list is large; the fetch uses a retry session.
- **Schedule frequency:** Sleeper recommends fetching this at most once per day.

## Acceptance Criteria
- [ ] On a successful run, `player-metadata/sleeper_nfl_players.json` in S3 reflects the
      latest Sleeper players list.
- [ ] Players lacking `first_name`/`last_name`/`position` are handled without corrupting the
      cache.
- [ ] A failed fetch leaves the previous cache intact.
- [ ] The processing pipeline ([BE-004](BE-004-data-processing-pipeline.md)) can resolve
      Sleeper `player_id`s from this cache.

## Sources
`src/player_metadata/handler.py`, `src/player_metadata/utils.py`.
