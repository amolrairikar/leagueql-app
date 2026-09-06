## Why

The landing-page league count is a hand-maintained atomic counter (`APP#STATS` / `LEAGUE_COUNT`)
that the processor increments on onboard, the API decrements on delete, and an orphan-cleanup
script decrements per orphan. Any missed update, partial delete, or orphaned league leaves the
counter permanently wrong with no self-correction. The count is simply "how many league
`METADATA` items exist," and DynamoDB already has a sparse index over exactly those items (GSI3),
so the count can be derived from truth instead of maintained by hand.

## What Changes

- The `sync-counts` Cloudflare worker computes the count by querying **GSI3** for `SK="METADATA"`
  (`Select=COUNT`, paginated across `LastEvaluatedKey`) and writes the total to KV on its existing
  hourly cron — replacing its `GetItem` on the `LEAGUE_COUNT` item.
- **BREAKING (internal data model):** the `APP#STATS` / `LEAGUE_COUNT` DynamoDB item is retired.
  The processor `+1`-on-onboard, the API `-1`-on-delete, and the orphan-script `-1` are removed.
- The public `/counts` endpoint (`get-counts` worker) is unchanged in shape and CORS behavior; it
  still serves `{ "leagueCount": <int> }` from the same KV key.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `backend/app-stats-league-count`: the count is no longer a maintained increment/decrement
  counter; it is **derived** from the number of league `METADATA` items via a GSI3 `COUNT` query
  published to KV on the hourly cadence. The "serve the count to the landing page" behavior is
  unchanged.

## Impact

- **Code:** `workers/sync-counts/index.js` (GetItem → paginated GSI3 Query); remove
  `update_league_count` from `src/processor/handler.py`, `src/api/helpers.py` (and its call in
  `src/api/routes.py`, re-export in `src/api/main.py`), and the decrement in
  `scripts/utility_scripts/find_orphaned_leagues.py`.
- **Data:** `APP#STATS` / `LEAGUE_COUNT` item no longer written or read (docs/db/dynamodb_spec.md).
- **Tests:** backend unit (processor + api) and component (onboarding + api seeding/asserts) drop
  their counter expectations.
- **No infra change:** GSI3 already exists; `sync-counts` already has the DynamoDB client, AWS
  credentials, table var, and KV binding.
