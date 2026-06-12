# BE-019: Sleeper Transactions (Waivers, Trades, Free Agents)

## Description
Builds a precomputed **transactions** view for Sleeper leagues — completed waiver claims,
trades (players and/or draft picks), free-agent adds/drops, and commissioner moves — with
opaque Sleeper player IDs resolved to player names/positions and roster IDs resolved to
team labels. The view is written to DynamoDB by the processor and read through the existing
query API ([BE-005](BE-005-query-precomputed-views-api.md)) under
`queryType=TRANSACTIONS#{season}`.

This is **Sleeper-only**: ESPN exposes no comparable transaction data, so the view is built
only for Sleeper leagues and ESPN leagues simply have no `TRANSACTIONS#` items (a query
404s). The feature is free for all Sleeper leagues — the only gate is the platform.

Sleeper raw transaction data is already fetched at onboard time (the onboarder's
`DATA_FETCH_TYPES` includes `transactions`) and stored per season in S3, so already-onboarded
leagues are backfilled by re-onboarding them (see Backfill below) — no re-fetch of historical
data is required.

## Scope
- Processor:
  - `src/processor/handler.py` — `_register_sleeper_raw_data` collects completed
    transactions; `compile_sleeper_transactions`, `_resolve_sleeper_transaction_players`,
    and `build_sleeper_roster_team_map` resolve players and teams; `_lambda_handler_impl`
    writes the `TRANSACTIONS#{season}` view (Sleeper-only, skipped when empty).
  - `src/processor/queries.py` — `QUERIES["TRANSACTIONS"]["SLEEPER"]` (passthrough; ordered
    newest-first).
  - `EntityType.TRANSACTIONS`.
- API: `QueryType.TRANSACTIONS` + `QUERY_TYPE_TO_SK_BASE` (`src/api/main.py`); served by the
  existing `GET /leagues/{leagueId}/query` handler unchanged.
- Backfill: `scripts/utility_scripts/backfill_sleeper_leagues.py` re-onboards every Sleeper
  league with the `reprocess_all` flag.
- Reprocess-all plumbing: `reprocess_all` threads through
  `src/common/onboarder_invoke.py::invoke_onboarder` → `src/onboarder/handler.py` →
  `OnboardingService` → `src/onboarder/writer.py::upload_results_to_s3` (manifest metadata)
  → processor (`reprocess_all` season selection). See
  [BE-004](BE-004-data-processing-pipeline.md).
- Output schema: `docs/db/dynamodb_spec.md` (`TRANSACTIONS#{season}`).

## Stored row shape (`TRANSACTIONS#{season}`, one item per season, `data` = list of rows)
Each row: `season`, `transaction_id`, `type` (`waiver` | `trade` | `free_agent` |
`commissioner`), `week` (Sleeper `leg`), `created` (epoch ms), `roster_ids` (string list),
`teams` (`[{roster_id, team_name, display_name}]`), `adds`/`drops`
(`[{player_id, player_name, position, roster_id}]`), `draft_picks`
(`[{round, season, from_roster_id, to_roster_id}]`), and `waiver_bid` (FAAB amount or null).

## Edge Cases
- **Only completed transactions:** records with `status != "complete"` (e.g. failed waiver
  claims) are dropped during registration.
- **Unknown players:** a player ID absent from the cached Sleeper player metadata resolves
  to `player_name = null` (position may also be null); the row still writes.
- **Trade variants:** trades may carry players only, draft picks only, or both;
  `draft_picks` map Sleeper `previous_owner_id → from_roster_id` and `owner_id →
  to_roster_id`.
- **Traded pick → drafted player:** a traded pick is matched to the player drafted with
  it via the pick's original slot owner (`roster_id`) → the draft's `slot_to_roster_id`
  seat → the draft pick at that `(round, draft_slot)`. `player_name` is null when the
  pick's draft has not happened yet (e.g. a future-season pick) or the draft data is
  unavailable.
- **Free agents / drop-only:** `adds` or `drops` may be empty; a `null` Sleeper map becomes
  `[]`.
- **Multi-roster transactions:** all rosters in `roster_ids` are resolved to team labels;
  unresolvable rosters fall back to `Roster {id}`.
- **Zero transactions:** a league/season with no completed transactions writes no
  `TRANSACTIONS#{season}` item; the query 404s (the frontend treats this as empty).
- **Offseason backfill:** a deep-offseason refresh may fetch no current-season data, but the
  historical season files already in S3 are still rebuilt under `reprocess_all`.
- **ESPN:** never produces a `TRANSACTIONS` view.

## Backfill
`scripts/utility_scripts/backfill_sleeper_leagues.py` enumerates every Sleeper league via the
GSI2 `platform=SLEEPER` index (one entry per canonical league) and asynchronously invokes the
onboarder Lambda with `requestType=REFRESH`, the existing `canonical_league_id`, and
`reprocess_all=True`. REFRESH preserves the league's METADATA (owner/members/subscription); a
full ONBOARD would Put-overwrite it. `reprocess_all` makes the processor rebuild every
season's views from the raw season files already in S3. Dry-run by default; `--execute` to
invoke. Idempotent.

## Acceptance Criteria
- [ ] Processing a Sleeper league with transactions writes `TRANSACTIONS#{season}` items
      whose rows have resolved player names and team labels.
- [ ] Failed/incomplete transactions are excluded; completed waivers, trades, and free
      agents are included.
- [ ] An unknown player ID yields `player_name = null` without failing the run.
- [ ] Trades with draft picks populate `draft_picks` with correct from/to roster IDs.
- [ ] A Sleeper league/season with no completed transactions writes no item, and the query
      returns `404`.
- [ ] ESPN leagues produce no `TRANSACTIONS` item.
- [ ] `GET /leagues/{leagueId}/query?platform=SLEEPER&queryType=TRANSACTIONS#{season}`
      returns the season's rows.
- [ ] The backfill script re-onboards every Sleeper league with `reprocess_all`, rebuilding
      transactions for all seasons; running it twice is idempotent.

## Authorization
Member-gating ([BE-016](BE-016-league-ownership-authorization.md)) is unchanged — Sleeper
reads stay open. No subscription/feature-flag paywall; the only gate is `platform=SLEEPER`.

## Sources
`src/processor/handler.py`, `src/processor/queries.py`, `src/api/main.py`,
`src/common/onboarder_invoke.py`, `src/onboarder/handler.py`,
`src/onboarder/onboarding_service.py`, `src/onboarder/writer.py`,
`scripts/utility_scripts/backfill_sleeper_leagues.py`, `docs/db/dynamodb_spec.md`,
`docs/api/openapi_spec.yaml`.
