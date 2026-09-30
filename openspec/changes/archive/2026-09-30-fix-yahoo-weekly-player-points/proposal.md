# Proposal

## Why

Every player in every Yahoo matchup lineup shows 0 points. The onboarder gets each week's
rosters with one league-wide call (all teams' rosters plus weekly player stats). Yahoo returns
the rosters for that call but silently drops the player stats, so every roster row's points are
null, and the processor turns null into 0. The same request for a single team does return the
weekly points: team 1's week-2 starters in the reported league add up to exactly its matchup
total.

## What Changes

- Yahoo onboarding fetches each week's roster and weekly player points **per team**. The team
  list comes from the league's team count, which is already known when seasons are resolved.
- The per-team results for a season and week are merged back into a single weekly roster record,
  so the raw-data shape the processor reads doesn't change.
- If a season's team count is unknown, its weekly rosters are skipped. Matchups still load, with
  empty lineups.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/league-onboarding`: adds a requirement to fetch Yahoo weekly rosters with player
  points per team.

## Impact

- `src/onboarder/yahoo_client.py`: builds the roster URLs, parses the single-team roster
  response, and merges the per-team results.
- About `num_teams` times more Yahoo roster calls per week. They are still capped by the
  existing Yahoo concurrency limit.
- No change to the processor, the API, DynamoDB views, or the frontend.
