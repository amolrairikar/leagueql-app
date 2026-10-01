# Proposal

## Why

Fetching every team's roster for every week (`fix-yahoo-weekly-player-points`) took a 9-season,
12-team Yahoo league from about 319 requests to 1,835. Yahoo now throttles these onboards with
HTTP `999 Request denied`. One throttled request drops its whole season, so users lose entire
years of standings and matchups just to get box-score detail.

## What Changes

- Yahoo onboarding and refresh **stop fetching per-team weekly rosters**. They return to the core
  requests (settings, standings, teams, draft, transactions, week calendar, weekly scoreboards), so
  every season onboards right away.
- After a Yahoo onboard or refresh, the league's seasons are marked **lineup-pending** on
  `METADATA`, and a backfill job is queued.
- A new **paced, resumable lineup backfill** fetches per-team weekly rosters and player points one
  season at a time, newest first, at a steady low rate. It saves progress as it goes. When Yahoo
  returns `999`, it stops right away and tries again later. A season that keeps getting throttled
  is marked failed and queued again by the next weekly scheduled refresh.
- When a season's lineups are complete, the backfill stores them and has the processor rebuild
  just that season. The processor merges the stored lineups into the season's matchups.
- `GET /leagues/{id}` returns `pending_lineup_seasons` and `failed_lineup_seasons`.
- The frontend shows a **notification bell** while any season's player scores are pending or
  failed. Lineup-dependent features show a pending state for those seasons, so users never see
  misleading zero-point lineups.

## Capabilities

### New Capabilities

- `backend/yahoo-lineup-backfill`: the queued, paced, resumable job that fills in Yahoo weekly
  lineups and player points per season, including throttle handling, retries, one job per league
  at a time, the lineup store, and pending/failed tracking.
- `frontend/lineup-data-status`: the notification bell and the shared pending state that
  lineup-dependent features use for seasons whose player scores haven't loaded yet.

### Modified Capabilities

- `backend/league-onboarding`: removes "Fetch Yahoo weekly rosters with player points per team".
  Adds a requirement that Yahoo onboard and refresh leave out rosters, mark seasons
  lineup-pending, and queue the backfill.
- `backend/data-processing-pipeline`: season selection also honors a list of seasons to
  reprocess, and Yahoo lineups come from the backfill's lineup store.
- `backend/league-metadata`: the metadata response includes the pending and failed lineup
  seasons.

## Impact

- **Backend:**
  - `src/onboarder/yahoo_client.py` (URL builder, matchup status)
  - `onboarding_service.py` and `writer.py` (pending flags, queueing)
  - new `src/onboarder/lineup_backfill.py` (a second Lambda from the onboarder package)
  - `src/processor/handler.py`
  - `src/api/routes.py`
- **Infrastructure:**
  - a new SQS queue and DLQ, and the backfill Lambda with limited concurrency
  - IAM for the onboarder and the backfill role
  - a DLQ alarm that alerts the existing Discord channel
  - the architecture diagram
- **Data:**
  - new `METADATA` attributes: `pending_lineup_seasons`, `failed_lineup_seasons`, and a lease
    timestamp
  - a new S3 object, `raw-api-data/{id}/yahoo_rosters/{season}.json`
  - updates to `docs/db/dynamodb_spec.md` and `docs/api/openapi_spec.yaml`
- **Frontend:** a league response type update, a lineup-status hook, a header bell, and pending
  handling in box scores, lineup efficiency, player records, matchup records, manager history and
  comparison, playoff-bracket box scores, and matchup previews.
- **Existing leagues:** no migration. Existing Yahoo leagues go through the backfill on their next
  refresh. Seasons onboarded under the per-team roster fix keep their current lineups.
