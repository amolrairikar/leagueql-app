# Design

## Context

See proposal.md (Why). Current flow:
1. The API or `league_refresh` invokes the onboarder Lambda.
2. `YahooClient.fetch_all` sends every request concurrently (`YAHOO_CONCURRENCY = 4`).
3. `upload_results_to_s3` writes `raw-api-data/{id}/{season}.json` per season, then merges
   `manifest.json`.
4. Writing the manifest triggers the processor (`s3:ObjectCreated:*`, suffix `manifest.json`),
   which picks seasons with `resolve_seasons_to_process`, or all of them with the `reprocess_all`
   manifest metadata.

Yahoo lineups are joined in `_register_yahoo_raw_data` from `rosters_week{W}` records in the
season file (`roster_lookup` → `_yahoo_lineups`).

Probes against a real league confirmed the following:
- **Single-team roster call:** `team/{key}/roster;week=W/players/stats` is the only roster call
  that returns weekly `player_points`. Both `teams` collection forms drop them.
- **999 throttling:** Yahoo's `999` isn't retried by `fetch_with_retry`, which only retries
  429/5xx.

## Goals / Non-Goals

**Goals:**
- Keep the onboard and refresh request count where it was before the per-team roster fix.
- Keep the backfill rate low enough that throttling is rare, and make it cheap when it happens.
- Never lose a season and never double-process a league.

**Non-Goals:**
- A manual "retry now" action. Failed seasons are retried by the weekly refresh.
- Migrating existing leagues. They pick up the backfill on their next refresh.
- Fewer Yahoo requests per lineup (batched player stats, our own scoring calculation). These were
  evaluated and rejected as more complex for small gains.

## Decisions

**1. The backfill runs as a second Lambda from the onboarder package**
(`src/onboarder/lineup_backfill.py`, `handler = "lineup_backfill.lambda_handler"`, same zip).
- This reuses `yahoo_client` (the roster URL builder and `_filter_rosters`), `utils.fetch_with_retry`
  and `describe_fetch_error`, `common.yahoo_tokens`, `common.tracing`, and the writer's S3 and
  DynamoDB clients.
- The alternative was a new top-level `src/` package. That would mean vendoring or duplicating the
  Yahoo parsing, which is exactly the drift `yahoo_player_stats_refresher` had to clean up.

**2. SQS standard queue, with a message chain per league and a concurrency cap.**
- **Message contents:** each message is `{canonical_league_id, attempt}`. The season to work on is
  read from `METADATA.pending_lineup_seasons` (newest first), so messages stay small, and new
  pending seasons added by a refresh are picked up by a chain that's already running.
- **Retries:** use the per-message `DelaySeconds=900`, which is SQS's maximum.
- **Concurrency:** `scaling_config.maximum_concurrency = 2` on the event source mapping limits how
  hard all backfills together can hit Yahoo.
- **Alternatives:**
  - EventBridge Scheduler one-off schedules: no queue backlog to look at, and no built-in global
    concurrency cap.
  - SQS FIFO: no per-message delay.

**3. A lease on METADATA instead of a FIFO group.**
- A conditional `UpdateItem` sets `lineup_backfill_lease_until` (15 minutes, longer than the
  Lambda's 900s timeout). A run that can't get the lease acknowledges its message and exits.
- This handles SQS redelivering a message and a refresh queuing a run while a chain is active.
  That's safe because the active chain re-reads the pending seasons.
- The lease is released on every exit path. If a run crashes, the lease expires on its own.

**4. Lineup store is a separate S3 object per season:** `raw-api-data/{id}/yahoo_rosters/{season}.json`
holding `{"weeks": {"<W>": [roster rows]}}`.
- Refresh rewrites `{season}.json`. If lineups lived in that file, every refresh would erase
  them, and the backfill and refresh would race on rewriting it.
- A separate object also makes progress tracking and incremental weeks easy: the weeks already
  stored are exactly the weeks to skip.

**5. Picking completed weeks.**
- `_filter_matchups` additionally records `status` (`preevent`/`midevent`/`postevent`).
- The backfill fetches a week only if all of its matchups are `postevent`.
- Team keys come from the matchup rows of that week, so no `teams` lookup or `num_teams` is
  needed.

**6. Publishing by copying the manifest onto itself.**
- After a season completes, `CopyObject` copies `manifest.json` onto itself with
  `MetadataDirective=REPLACE`. The new metadata carries `reprocess_seasons=<season>`,
  `correlation_id`, and the trace context from `inject_context`.
- S3 copies the body itself from the latest version, so a concurrent refresh's manifest update
  can't be overwritten with an old copy. `ObjectCreated:Copy` already triggers the processor.
- The processor treats `reprocess_seasons` like `reprocess_all`: it skips the comparison with the
  previous manifest and processes exactly the listed seasons.

**7. Processor merge.**
- For `YAHOO`, after loading each season to process, read `yahoo_rosters/{season}.json`
  (a missing object means none).
- For each stored week, replace any `rosters_week{W}` records from the season file with a single
  record built from the store.
- No changes to `_yahoo_lineups`. With no lineups, the starter and bench lists stay empty.

**8. Pacing and the circuit breaker.**
- Requests go out one at a time at about 1 per second, the same `TARGET_INTERVAL` pattern as
  `yahoo_player_stats_refresher`.
- The run checkpoints the store after every completed week.
- On the first `999`, it stops sending requests, checkpoints, releases the lease, and re-sends the
  message with `attempt+1` and `DelaySeconds=900`. `attempt` resets to 0 when a season completes.
- Once `attempt == 8`, the season moves to `failed_lineup_seasons`.
- A 401 is already handled with a token refresh in `_fetch_with_auth_retry`.
- `YahooReauthRequired`, a 403/404, or a missing METADATA item ends the chain.

**9. Pending and failed bookkeeping lives on METADATA as string sets**
(`pending_lineup_seasons`, `failed_lineup_seasons`). DynamoDB set `ADD`/`DELETE` updates are
atomic and safe to repeat. The onboarder writes them in the same transaction as the league
records. The API returns them as sorted lists.

**10. Frontend status comes from one hook.**
- `use-lineup-backfill.ts`, shaped like `use-is-owner.ts`, exposes `isLineupUnavailable(season)`.
- Every lineup-dependent feature goes through this one hook so they behave the same.
- The bell sits in the app header and uses the existing inline-alert style, not a global error
  store.

## Risks / Trade-offs

- **Yahoo's limit is per app or IP, not per user** → the backfill cap (2) plus pacing bounds
  total traffic. Scheduled refreshes are already paced separately. If 999s are still common, lower
  the rate with a setting rather than a code change.
- **Lineup-dependent stats stay incomplete until the backfill finishes** (about 3–4 minutes per
  season, longer if throttled) → the bell and per-feature notes make it visible. The newest season
  goes first.
- **The bell shows briefly every week in season** (each refresh marks the current season pending
  until its new week is backfilled) → acceptable. It only adds one week of requests and normally
  clears within minutes.
- **Existing leagues onboarded before the per-team roster fix keep 0-point lineups** for past
  seasons until a full re-onboard → accepted (no migration, per the user's decision).
- **The processor rebuilds a season once per completed backfill** → this is one extra processor
  run per season, which is negligible.

## Migration Plan

1. Deploy the infrastructure first: the queue, DLQ, backfill Lambda, IAM, and the alarm. The
   onboarder's queue URL environment variable must exist before the new onboarder code runs.
2. Deploy the backend (onboarder, backfill, processor, API), then the frontend. The frontend
   tolerates the new fields being absent.
3. **Rollback:** revert the onboarder to per-team rosters and disable the event source mapping.
   The pending sets do nothing on their own, and the frontend treats missing lists as empty.
