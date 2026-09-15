## Why

The refresh "already up to date" guard permanently blocks in-season refreshes for ESPN
leagues. ESPN's schedule endpoint returns the entire season's matchups up front (weeks
1–18), so the processor writes a `MATCHUPS#{season}#WEEK#{week}` item for every future,
unplayed week (with 0–0 scores). `get_latest_stored_matchup` returns the largest stored
SK — always the final scheduled week — so the guard sees the league as current for the
whole season and returns `409`. Sleeper is unaffected because Sleeper only returns played
weeks. This blocks the core refresh feature for every ESPN user during the season.

## What Changes

- The "already up to date" refresh guard SHALL compare current NFL state against the latest
  **played** stored week, not the raw maximum `MATCHUPS#` SK. A stored week counts as played
  only when it has a real result (a non-zero score or a decided winner); pre-stored future
  weeks with 0–0 scores and no winner are ignored.
- `get_latest_stored_matchup` (in `src/api/helpers.py`) changes from "largest SK" to "latest
  played week", walking `MATCHUPS#` items newest-first and returning the first week whose
  stored body shows a played result.
- No change to what is stored: ESPN continues to persist its full-season schedule (Option A —
  filtering unplayed weeks at write time — is explicitly out of scope here).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/league-refresh`: The "Short-circuit when already up to date" requirement's
  "Already current" scenario changes so that the comparison is against the latest **played**
  stored week rather than the latest stored matchup SK, ensuring ESPN's pre-stored future
  weeks do not make a league look current.

## Impact

- Code: `src/api/helpers.py` (`get_latest_stored_matchup` — now reads item bodies to detect
  played weeks, not just the SK), and its callers in `src/api/routes.py` (behavior of the
  refresh guard). No API contract, DynamoDB schema, or S3 layout change.
- Tests: backend unit tests for `get_latest_stored_matchup` (played vs. unplayed weeks),
  and backend component tests for the ESPN refresh path (an ESPN league whose only "newer"
  stored weeks are unplayed must be allowed to refresh; a genuinely current league must still
  return `409`).
