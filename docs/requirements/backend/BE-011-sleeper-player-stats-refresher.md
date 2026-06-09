# BE-011: Sleeper Player Stats Refresher

## Description
Scheduled Lambda that fetches per-player season scoring stats from Sleeper and caches them
in S3. The processing pipeline uses these stats to compute draft analytics — `total_points`,
`actual_position_rank`, `draft_rank_delta`, and `vorp` — for Sleeper leagues. Requests are
rate-limited to stay within Sleeper's API limits.

The cache is a per-player, per-season map: `{player_id: {season: stats}}`. A refresh only
fetches the players selected this run (active players + D/ST) for a single `season`, so the
Lambda **must not** overwrite the cache with only that slice. Instead it reads the existing
cache object first and **deep-merges** the freshly fetched `{player_id: {season: stats}}`
into it, so previously cached seasons for the same player and players not refreshed this run
are preserved.

## Scope
- Lambda: `src/sleeper_player_stats_refresher/` (`handler.py`, `utils.py`).
- Sources: per-player stats
  `https://api.sleeper.com/stats/nfl/player/{player_id}?season_type=regular&season={season}`;
  NFL state from `https://api.sleeper.app/v1/state/nfl`.
- Inputs: player IDs from `player-metadata/sleeper_nfl_players.json`.
- Output: S3 key `player-stats/sleeper_nfl_player_stats.json`, written as a deep-merge of the
  freshly fetched stats into the existing object at the same key (read-modify-write).
- Rate limit: `TARGET_INTERVAL = 60 / 925` (~925 requests/min ceiling).
- Event overrides (used for on-demand and integration-test runs only; the scheduled
  S3-triggered invocation carries none of them and retains full production behavior):
  - `season`: forces a refresh for that season and bypasses the live NFL-state check
    (including the off-season skip).
  - `max_players`: caps the run at the first N active players instead of the full
    fan-out, so an integration test can validate the end-to-end path in seconds rather
    than minutes. Omitted in production → all active players are processed.
  - `output_key`: reads from and merges into this S3 key instead of the production
    `player-stats/sleeper_nfl_player_stats.json`, so a test run does not clobber the
    live cache. Omitted in production → the canonical output key is used.

## Edge Cases
- **Partial refresh must not wipe the cache:** a run fetches only the selected players for a
  single `season`. The Lambda reads the existing cache and deep-merges, so other seasons for
  the same player and players outside this run's selection survive. It never replaces the
  whole object with just this run's slice.
- **No existing cache yet:** when the output object does not exist (`NoSuchKey`/`404`), start
  from an empty map and write the freshly fetched stats — the first run bootstraps the cache.
- **Player selection:** fetch stats for players with `status == "Active"`. Team defenses
  (D/ST) carry no `status` field in Sleeper's metadata (only an `active` boolean), so they
  are always fetched via a `position == "DEF"` exception — otherwise defenses are dropped and
  their draft picks get null `total_points` / position ranks.
- **NFL state fetch fails:** log a warning and continue.
- **Per-player stats fetch fails:** skip that player without aborting the whole run.
- **Rate limiting:** pace requests to ~`TARGET_INTERVAL` between calls to avoid 429s.
- **Off-season / no stats yet:** players with no stats for the season are handled (null).
- **Player metadata cache missing/stale:** depends on [BE-010](BE-010-player-metadata-refresher.md);
  must handle an empty/partial player list.
- **Large fan-out:** thousands of players → long runtime; must fit within Lambda timeout or
  process incrementally.
- **`max_players` override:** when supplied, only the first N active players are processed;
  the resulting cache is intentionally partial and must not be used to overwrite the
  production cache (pair with `output_key`).

## Acceptance Criteria
- [ ] On a successful run, `player-stats/sleeper_nfl_player_stats.json` contains current
      regular-season stats for available players.
- [ ] A refresh for one `season` deep-merges into the existing cache: previously cached
      seasons for the same player and players not in this run's selection are preserved.
- [ ] When no cache object exists yet, the run starts from empty and writes the fetched stats.
- [ ] Requests are paced to stay under the Sleeper rate limit.
- [ ] Individual player failures are skipped without failing the run.
- [ ] The processing pipeline can compute `total_points` / `vorp` / position ranks from this
      cache for Sleeper drafts.
- [ ] A `max_players` + `output_key` invocation exercises the full S3-read → live-fetch →
      S3-write path against a small player subset and writes to the override key, leaving the
      production cache untouched.

## Sources
`src/sleeper_player_stats_refresher/handler.py`, `src/sleeper_player_stats_refresher/utils.py`.
