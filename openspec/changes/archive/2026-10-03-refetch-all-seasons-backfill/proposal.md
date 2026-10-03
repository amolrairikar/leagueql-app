# Proposal

## Why

`scripts/utility_scripts/backfill_leagues.py` invokes the onboarder with `REFRESH` and
`reprocess_all`. A REFRESH fetches only the league's latest season from the platform, and
`reprocess_all` only rebuilds views from the raw season files already in S3. Raw data for an
older season that was fetched wrong can't be repaired this way. For example, ESPN 2018 seasons
were fetched without box-score rosters before `fix-espn-2018-boxscores`. A full re-onboard would
re-fetch them, but it overwrites METADATA (owner, members, auto-refresh opt-in). For ESPN and
Yahoo it would also create a new canonical league ID.

## What Changes

- The onboarder accepts a `refetchAll` event field. On a `REFRESH` with `refetchAll=true`, it
  fetches every season of the league's history from the platform, overwrites each season's raw
  S3 file under the existing canonical prefix, and rebuilds every season's views. It uses the
  same REFRESH write path, so METADATA is preserved.
- `refetchAll` is ignored for `ONBOARD` and `MIGRATE`. An ONBOARD already fetches every season,
  and a MIGRATE keeps its current behavior.
- `invoke_onboarder` gains a `refetch_all` argument that maps to the `refetchAll` field.
- `backfill_leagues.py` gains an opt-in `--refetch-all` flag. Without it, the script behaves as
  before: it reprocesses existing raw data and re-fetches only the latest season.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/league-refresh`: adds a requirement for a REFRESH that re-fetches every season.
- `backend/sleeper-transactions`: the backfill requirement gains the `--refetch-all` mode.

## Impact

- **Backend:** `src/common/onboarder_invoke.py`, `src/onboarder/handler.py`,
  `src/onboarder/onboarding_service.py`.
- **Scripts:** `scripts/utility_scripts/backfill_leagues.py`.
- **Tests:** onboarder, invoke-helper, and backfill-script unit tests, plus a league-refresh
  component scenario.
- **API / frontend / data model:** no change. The API never sends `refetchAll`, and the manifest
  reuses the existing `reprocess_all=true` metadata.
