# BE-011: Sleeper Player Stats Refresher

## Description
Scheduled ECS Fargate task that fetches per-player season scoring stats from Sleeper and
caches them in S3. The processing pipeline uses these stats to compute draft analytics —
`total_points`, `actual_position_rank`, `draft_rank_delta`, and `vorp` — for Sleeper leagues.
Requests are rate-limited to stay within Sleeper's API limits.

The full per-player fan-out (thousands of players, paced to ~925 req/min) regularly exceeds
Lambda's hard 15-minute timeout, so the refresher runs as a **Fargate task** (no execution-
time cap) rather than a Lambda. It is triggered on a **weekly CloudWatch Events schedule**,
`cron(15 12 ? * TUE *)` (UTC) — 15 minutes after the Tuesday player-metadata refresh
(BE-010) so the metadata it reads is fresh.

The cache is a per-player, per-season map: `{player_id: {season: stats}}`. A refresh only
fetches the players selected this run (active players + D/ST) for a single `season`, so the
task **must not** overwrite the cache with only that slice. Instead it reads the existing
cache object first and **deep-merges** the freshly fetched `{player_id: {season: stats}}`
into it, so previously cached seasons for the same player and players not refreshed this run
are preserved.

## Scope
- Container: `src/sleeper_player_stats_refresher/` (`handler.py`, `utils.py`, `Dockerfile`,
  `requirements.txt`). Packaged as a Docker image in ECR and run as a Fargate task; the
  entrypoint is `main()` (`python handler.py`), not a Lambda handler.
- Trigger: weekly CloudWatch Events rule `cron(15 12 ? * TUE *)` (UTC) → ECS `RunTask`
  (Fargate launch type) in the shared outbound-only VPC. **Not** S3-event driven.
- Sources: per-player stats
  `https://api.sleeper.com/stats/nfl/player/{player_id}?season_type=regular&season={season}`;
  NFL state from `https://api.sleeper.app/v1/state/nfl`.
- Inputs: player IDs from `player-metadata/sleeper_nfl_players.json`.
- Output: S3 key `player-stats/sleeper_nfl_player_stats.json`, written as a deep-merge of the
  freshly fetched stats into the existing object at the same key (read-modify-write).
- Rate limit: `TARGET_INTERVAL = 60 / 925` (~925 requests/min ceiling).
- Environment-variable overrides (used for on-demand and integration-test runs only; the
  scheduled invocation sets none of them and retains full production behavior):
  - `SEASON`: forces a refresh for that season and bypasses the live NFL-state check
    (including the off-season skip).
  - `MAX_PLAYERS`: caps the run at the first N active players instead of the full
    fan-out, so an integration test can validate the end-to-end path in seconds rather
    than minutes. Omitted in production → all active players are processed.
  - `OUTPUT_KEY`: reads from and merges into this S3 key instead of the production
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
- **Large fan-out:** thousands of players → long runtime. Running as a Fargate task removes
  the 15-minute Lambda timeout, so the full fan-out completes in a single run with no need to
  chunk or checkpoint.
- **`MAX_PLAYERS` override:** when supplied, only the first N active players are processed;
  the resulting cache is intentionally partial and must not be used to overwrite the
  production cache (pair with `OUTPUT_KEY`).

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
- [ ] A `MAX_PLAYERS` + `OUTPUT_KEY` run exercises the full S3-read → live-fetch →
      S3-write path against a small player subset and writes to the override key, leaving the
      production cache untouched.
- [ ] The refresher runs as a scheduled Fargate task (no 15-minute cap); a full fan-out that
      exceeds 15 minutes completes in a single run and writes the canonical cache key.

## Sources
`src/sleeper_player_stats_refresher/handler.py`, `src/sleeper_player_stats_refresher/utils.py`.
