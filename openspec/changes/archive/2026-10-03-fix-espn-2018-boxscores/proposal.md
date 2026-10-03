# Proposal

## Why

ESPN 2018 seasons show matchup scores but empty box scores (no starters or bench). The onboarder
requests every season up to `V2_CUTOFF` (2018) from ESPN's `leagueHistory/{id}?seasonId=…`
endpoint, which ignores the `mBoxscore` view, so each matchup's `home`/`away` arrives without
`rosterForMatchupPeriod` / `rosterForCurrentScoringPeriod`. Every stored prod 2018 payload has no
rosters in any week. The same per-week request against
`seasons/2018/segments/0/leagues/{id}` returns full rosters whose starter points sum to each
team's score.

## What Changes

- Per-week ESPN `matchups` requests for 2018 and later use the
  `seasons/{season}/segments/0/leagues/{id}` endpoint.
- Every other 2018 data type (users, settings, draft picks, player scoring totals) and every data
  type for seasons before 2018 keep using `leagueHistory`. `V2_CUTOFF` and the player-totals
  parsing it controls are unchanged.
- No processor, API or frontend change: the processor already compiles box scores from these
  roster fields.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/league-onboarding`: adds a requirement fixing which ESPN endpoint serves per-week
  matchups.

## Impact

- **Backend:** `src/onboarder/espn_client.py` (`_build_all_request_urls`).
- **Tests:** onboarder URL unit tests; a processor unit test on a 2018-shaped box score.
- **Data:** existing leagues keep empty 2018 box scores until their 2018 season is re-fetched.
  `backfill_leagues.py` only reprocesses raw S3 data and re-fetches the latest season, so it
  does not fix them; a full re-onboard does.
