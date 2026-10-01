# Tasks

## 1. Onboarder: core-only Yahoo fetch

- [x] 1.1 In `src/onboarder/yahoo_client.py`:
  - remove the per-team `rosters_week{W}_t{T}` URLs from `_build_request_urls`
  - extract a reusable per-team roster URL builder and a single-team roster parser around
    `_filter_rosters`

  Verify by updating `tests/unit/onboarder/test_yahoo_client.py`: no roster URLs are built, the
  request count is 6 per season plus 1 per week, and the builder/parser test passes.
- [x] 1.2 Make `_filter_matchups` emit each matchup's `status`. Verify with a unit test covering
  preevent, midevent and postevent rows.
- [x] 1.3 Make `write_league_records` (`src/onboarder/writer.py`) set the lineup status for YAHOO:
  - add the onboarded seasons to `pending_lineup_seasons`
  - on refresh, move `failed_lineup_seasons` into pending

  Verify with writer unit tests for onboard, refresh, and non-Yahoo (where nothing changes).
- [x] 1.4 After a successful YAHOO run, queue the backfill message
  (`LINEUP_BACKFILL_QUEUE_URL`). It's best-effort: a send failure is logged and the onboard still
  succeeds. Verify with `tests/unit/onboarder/test_onboarding_service.py` (sent, send failure
  tolerated, ESPN/Sleeper not sent).
- [x] 1.5 Update the backend component scenario `tests/component/features/onboard_to_processed.feature`
  (Yahoo): METADATA is pending and a message is queued (moto SQS). Verify with
  `pipenv run behave tests/component`.

## 2. Lineup backfill Lambda

- [x] 2.1 Create `src/onboarder/lineup_backfill.py` with the SQS handler and the lease:
  - a conditional update on `lineup_backfill_lease_until`
  - skip when the lease is held
  - release the lease on every exit path

  Verify with `tests/unit/onboarder/test_lineup_backfill.py` lease tests (held, expired, missing
  METADATA).
- [x] 2.2 Pick the season and the weeks to fetch:
  - choose the newest pending season
  - read the season file and the lineup store
  - keep weeks where every matchup is postevent and the week isn't already stored
  - take team keys from the matchups

  Verify with unit tests (finished season, in-progress season, resuming with stored weeks, nothing
  pending).
- [x] 2.3 Fetch at a steady pace, one request at a time, with a checkpoint after each week, using
  the owner's token through `common.yahoo_tokens`. Verify with unit tests (requests are sequential,
  pacing sleep is patched, the store is written after each week).
- [x] 2.4 Handle 999 and permanent errors:
  - on 999, stop, checkpoint, and re-queue with `DelaySeconds=900` and `attempt+1`
  - at attempt 8, move the season to failed and queue the next season
  - on reauth, 403/404, or a missing league, mark the season failed or exit with no retry

  Verify with unit tests for each path.
- [x] 2.5 Publish a completed season:
  - copy the manifest onto itself with `reprocess_seasons` plus correlation and trace metadata
  - `DELETE` the season from `pending_lineup_seasons`
  - queue the next run if seasons are still pending

  Verify with unit tests (moto S3 copy metadata, DynamoDB set update, chained message).

## 3. Processor

- [x] 3.1 Honor the manifest metadata `reprocess_seasons` (a comma list) in `src/processor/handler.py`,
  skipping the comparison with the previous manifest. Verify with tests in `tests/unit/processor/`.
- [x] 3.2 For YAHOO, load `yahoo_rosters/{season}.json` when present and let it override the
  season file's `rosters_week*` records. Verify with `tests/unit/processor/test_yahoo.py`:
  - store lineups are attached and the starter sum equals the matchup score
  - legacy in-file rosters are used when there's no store
  - empty lineups when there's neither
- [x] 3.3 Add a component scenario: Yahoo onboard → backfill run (Yahoo mocked) → processor
  rebuilds MATCHUPS with lineups → the season is no longer pending, and a 999 leaves the season
  pending with a delayed message. Verify with `pipenv run behave tests/component`.
- [x] 3.4 Document the lineup store, the `reprocess_seasons` manifest metadata and the new
  METADATA attributes in `docs/db/dynamodb_spec.md`. Verify by reviewing the documented key
  shapes against the code.

## 4. API

- [x] 4.1 Return `pending_lineup_seasons` and `failed_lineup_seasons` as sorted lists (empty when
  absent) from `GET /leagues/{leagueId}` in `src/api/routes.py`. Verify with the API unit tests
  and the league-metadata component scenario.
- [x] 4.2 Add both fields to the league response schema in `docs/api/openapi_spec.yaml`. Verify
  the YAML parses and the fields match the response.

## 5. Infrastructure

- [x] 5.1 In `infrastructure/regional/main.tf`:
  - SQS queue and DLQ (`maxReceiveCount` 3)
  - backfill Lambda (onboarder zip, handler `lineup_backfill.lambda_handler`, timeout 900, Yahoo
    env vars)
  - event source mapping with `maximum_concurrency = 2`
  - onboarder env var `LINEUP_BACKFILL_QUEUE_URL`
  - DLQ-depth alarm to the existing alert topic

  Verify with `terraform validate` and `terraform plan` in dev.
- [x] 5.2 In `infrastructure/global/{dev,prod}/main.tf`:
  - onboarder `sqs:SendMessage`
  - backfill role: DynamoDB Get/UpdateItem, S3 Get/Put/Copy on `raw-api-data/*`, SQS
    receive/delete/send, KMS decrypt, SSM Yahoo client id, logs

  Verify with `terraform validate` and `terraform plan` in dev.
- [x] 5.3 Add the queue and the backfill Lambda to `docs/architecture/architecture_diagram.py`
  and regenerate the PNG (`pipenv run python docs/architecture/architecture_diagram.py`). Verify
  the PNG shows the new components.

## 6. Frontend

- [x] 6.1 Add `pending_lineup_seasons` and `failed_lineup_seasons` to the league response type
  (`frontend/src/components/api/types.ts`) and the MSW default handler. Verify with
  `npm run build:ci`.
- [x] 6.2 Create the `frontend/src/features/lineup_backfill/use-lineup-backfill.ts` hook
  (bypasses demo mode and the no-league case; a failed fetch counts as nothing pending) and the
  `lineup-backfill-bell.tsx` header bell. Verify with a jest-cucumber feature: hidden, pending,
  failed, and fetch-error states.
- [x] 6.3 Add a pending placeholder to the box score (`components/box-score-card.tsx` and its
  matchups usage). Verify with the matchups feature scenario for a pending season.
- [x] 6.4 Leave pending and failed seasons out of, and show an inline note in:
  - lineup efficiency
  - player records
  - matchup records
  - manager history
  - manager comparison
  - playoff-bracket box scores
  - matchup preview

  Verify with an added scenario in each feature's `__tests__`. Box scores in matchup records,
  manager history, manager comparison and the playoff bracket all render the shared
  `BoxScoreCard`, so they are covered by `lineup_backfill/__tests__/box-score-pending.feature`.
  Matchups (box score and preview) and player records have their own scenarios.
- [x] 6.5 Run `npm run format:fix`, `npm run lint`, `npm run build:ci` and `npm run test` from
  `frontend/`. All must pass.

## 7. Integration checks

- [x] 7.1 Run `npx @fission-ai/openspec@latest validate --all`,
  `pipenv run ruff check --fix . && pipenv run ruff format .`, `pipenv run pytest tests/unit`, and
  `pipenv run behave tests/component`. All must pass.
- [x] 7.2 Run a dev end-to-end onboard of the 2018–2026 Yahoo league. Check that:
  - the onboarder makes about 319 requests with no 999s
  - all seasons show right away and the bell is shown
  - the backfill fills seasons newest first, the processor logs `Seasons to process: [<season>]`
    for each, and the bell clears

  Spot-check that one team's starter sum equals its matchup score.
