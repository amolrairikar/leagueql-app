# BE-011: Sleeper Player Stats Refresher

## Description
Scheduled Lambda that fetches per-player season scoring stats from Sleeper and caches them
in S3. The processing pipeline uses these stats to compute draft analytics — `total_points`,
`actual_position_rank`, `draft_rank_delta`, and `vorp` — for Sleeper leagues. Requests are
rate-limited to stay within Sleeper's API limits.

## Scope
- Lambda: `src/sleeper_player_stats_refresher/` (`handler.py`, `utils.py`).
- Sources: per-player stats
  `https://api.sleeper.com/stats/nfl/player/{player_id}?season_type=regular&season={season}`;
  NFL state from `https://api.sleeper.app/v1/state/nfl`.
- Inputs: player IDs from `player-metadata/sleeper_nfl_players.json`.
- Output: S3 key `player-stats/sleeper_nfl_player_stats.json`.
- Rate limit: `TARGET_INTERVAL = 60 / 850` (~850 requests/min ceiling).

## Edge Cases
- **NFL state fetch fails:** log a warning and continue.
- **Per-player stats fetch fails:** skip that player without aborting the whole run.
- **Rate limiting:** pace requests to ~`TARGET_INTERVAL` between calls to avoid 429s.
- **Off-season / no stats yet:** players with no stats for the season are handled (null).
- **Player metadata cache missing/stale:** depends on [BE-010](BE-010-player-metadata-refresher.md);
  must handle an empty/partial player list.
- **Large fan-out:** thousands of players → long runtime; must fit within Lambda timeout or
  process incrementally.

## Acceptance Criteria
- [ ] On a successful run, `player-stats/sleeper_nfl_player_stats.json` contains current
      regular-season stats for available players.
- [ ] Requests are paced to stay under the Sleeper rate limit.
- [ ] Individual player failures are skipped without failing the run.
- [ ] The processing pipeline can compute `total_points` / `vorp` / position ranks from this
      cache for Sleeper drafts.

## Sources
`src/sleeper_player_stats_refresher/handler.py`, `src/sleeper_player_stats_refresher/utils.py`.
