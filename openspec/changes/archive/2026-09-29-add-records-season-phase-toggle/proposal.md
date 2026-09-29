# Proposal

## Why

Leagues with 2-week playoff matchups record each postseason game with two weeks of points. On
`/player_records` and `/matchup_records` those games rank alongside single-week regular-season
games, so they crowd out the Highest Team Score, Highest Matchup Score, Biggest Blowout, and
per-position player boards.

## What Changes

- Both records pages get a "Regular season / Postseason" switch in their filter bar.
- The default is Regular season: only regular-season matchups (`playoff_tier_type` `NONE`) feed the
  record boards. Switching to Postseason ranks only playoff matchups (any bracket tier).
- The switch composes with the existing Season (and Manager) filters and clears the open box score.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/player-records`: records are filtered by season phase.
- `frontend/matchup-records`: records are filtered by season phase.

## Impact

- **Frontend**: `frontend/src/lib/matchups.ts` (`isRegularSeasonMatchup`, `SeasonPhase`), new
  `frontend/src/components/season-phase-toggle.tsx`, `player_records/player-records.tsx`,
  `matchup_records/matchup-records.tsx`; component tests beside each page and unit tests for the
  helper.
- No backend, API, DynamoDB, or infrastructure change.
