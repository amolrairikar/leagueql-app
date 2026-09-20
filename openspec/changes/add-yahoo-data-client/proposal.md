## Why

Yahoo OAuth account-linking shipped, but a linked user who tries to onboard a Yahoo league only
gets a neutral "coming soon" signal — the onboarder is never invoked and no Yahoo data is
fetched (`src/api/routes.py`). This change builds the Yahoo Fantasy data client so a Yahoo league
onboards through the same async pipeline as ESPN and Sleeper, giving Yahoo users the same
standings/matchups/draft/transactions analytics with no extra input beyond the one-time OAuth
link.

## What Changes

- Add a **Yahoo Fantasy data client** in the onboarder that authenticates with the linked user's
  Bearer token, resolves the entered numeric league id to Yahoo's season-specific `league_key`,
  walks the per-season `renew` chain to onboard the **full league history**, and fetches
  settings/standings/teams/matchups/draft/transactions/player scoring — normalizing Yahoo's JSON
  into the same grouped shapes the processor already consumes.
- Add **Yahoo transforms** to the processor (DuckDB) that produce the identical precomputed view
  schemas ESPN/Sleeper produce (teams, matchups, standings, playoff bracket, draft, league
  settings), including deriving the playoff bracket from playoff-week matchups (Yahoo has no
  bracket endpoint).
- Replace the `YAHOO_COMING_SOON` onboarding gate with the real onboarder invoke; a linked Yahoo
  **refresh** is likewise gated on a valid link.
- Enable the onboarder to obtain/refresh Yahoo tokens mid-run (onboarding can outlast Yahoo's
  ~1 hr token life): extract token management into a shared module and grant the onboarder role
  cross-region KMS decrypt + SSM read (fulfils the OAuth increment's deferred cross-region-KMS
  follow-up).
- Frontend: after a successful link, resume onboarding and **poll to completion** (the standard
  ESPN/Sleeper flow) instead of showing "coming soon".

## Capabilities

### New Capabilities
- `backend/yahoo-transactions`: Fetch Yahoo league transactions (adds/drops/trades) and build the
  precomputed `TRANSACTIONS#{season}` view with player names and team labels resolved, mirroring
  `backend/espn-transactions` and `backend/sleeper-transactions`.
- `backend/yahoo-player-stats-refresher`: A scheduled ECS Fargate task that fetches Yahoo NFL
  player metadata + season scoring (across the player pool) using a dedicated service Yahoo
  credential and caches them to S3, where the processor reads them to resolve player
  names/positions and compute draft analytics — mirroring `backend/sleeper-player-stats-refresher`
  and `backend/player-metadata-refresher`.

### Modified Capabilities
- `backend/league-onboarding`: Onboarding (and refresh) SHALL support Yahoo leagues — resolving
  the `league_key`/season history from the linked user's account, obtaining a valid Yahoo access
  token in the onboarder, and fetching the same data domains as ESPN/Sleeper.
- `backend/data-processing-pipeline`: The pipeline SHALL transform raw Yahoo data into the same
  per-season precomputed view schemas as ESPN/Sleeper.
- `frontend/connect-yahoo-league`: A linked Yahoo league SHALL onboard and poll to completion
  (the ESPN/Sleeper success flow) — replacing the "coming soon" onboarding notice — while keeping
  the `YAHOO_AUTH` reconnect prompt.

## Impact

- **Backend code:** new `src/onboarder/yahoo_client.py`; new shared `src/common/yahoo_tokens.py`
  (extracted from `src/api/yahoo_oauth.py`, which re-imports it); `_build_client` in
  `src/onboarder/onboarding_service.py`; `register_raw_data` + a new `_register_yahoo_raw_data`
  in `src/processor/handler.py`; `YAHOO` query sub-keys in `src/processor/queries.py`; the Yahoo
  branch of `onboard_league` in `src/api/routes.py`.
- **Frontend:** `frontend/src/features/connect_league/{yahoo-connect-return.tsx,api-calls.ts}`.
- **New component:** a Yahoo player-data ECS Fargate task (`src/yahoo_player_stats_refresher/`,
  Dockerfile + `main()`) on a schedule, reading a dedicated service Yahoo credential
  (service account + league resolved from SSM) and writing `player-metadata/yahoo_nfl_players.json` +
  `player-stats/yahoo_nfl_player_stats.json` to S3 — mirroring `sleeper_player_stats_refresher`.
- **External integration:** the onboarder and the player-data task now call the Yahoo Fantasy
  Sports API (`fantasysports.yahooapis.com`) — a new external dependency for the diagram.
- **Infra:** onboarder Lambda gains Yahoo env vars and KMS-decrypt/SSM-read IAM; the new ECS task
  gains its task definition, schedule, S3 write, and KMS/SSM/DynamoDB access
  (`infrastructure/regional/main.tf`, `infrastructure/global/{dev,prod}/main.tf`).
- **Docs:** `docs/api/openapi_spec.yaml` (platform enum), `docs/db/dynamodb_spec.md` (`YAHOO` in
  platform enums), `docs/architecture/`.
- **Prerequisite / sequencing:** the `add-yahoo-league-support` change (OAuth linking, still open
  at task 6.2/7.x) SHALL be archived first so the `backend/yahoo-oauth` and
  `frontend/connect-yahoo-league` base specs are live for this change's deltas to reference; this
  change folds in that change's deferred follow-ups 7.1 (data client) and 7.2 (cross-region KMS).
- **Not in scope:** live-API integration tests under `tests/integration/yahoo/` (needs a real
  linked test account) — tracked as a follow-up.
