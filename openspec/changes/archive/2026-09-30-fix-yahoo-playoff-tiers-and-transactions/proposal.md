# Proposal

## Why

Yahoo leagues show two champions per season. The processor treats every playoff game that isn't in
the consolation bracket as a championship-path game, so a 3rd-place game in the final week also
counts as a title game. Its winner gets `champion = Yes`, a second `position = 1` bracket match,
and a second "Finals" label. Separately, Yahoo transactions have these problems:
- trades are stored with no players or teams
- `created` is epoch seconds as text, so the UI shows an invalid date
- `week` is always empty, so pickup impact is credited from week 0

## What Changes

- Yahoo playoff games are placed in tiers by bracket path. A game is winners-bracket only while
  neither team has lost a playoff game yet. Placement games (3rd, 5th) are winners-consolation.
  Consolation-bracket games (teams that missed the playoffs) are losers-tier and are left out of
  the bracket.
- The season champion is the winner of the last winners-bracket week, not a hard-coded week 16/17.
  This applies to all platforms.
- Yahoo trades credit each traded player to the receiving team (add) and the sending team (drop).
- Yahoo `created` is stored as epoch milliseconds, like ESPN and Sleeper.
- Yahoo onboarding fetches each season's week calendar, and the processor resolves each
  transaction's week from its time.
- Spec wording for Yahoo requirements is made generic (no raw API field names).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/data-processing-pipeline`: Yahoo playoff tiering, a single champion per season, and
  generic wording for the Yahoo settings scenario.
- `backend/yahoo-transactions`: trades, `created` units, the resolved week, and generic fetch wording.
- `backend/league-onboarding`: the Yahoo week-calendar fetch.

## Impact

- **Backend**: `src/processor/handler.py`, `src/processor/queries.py` (STANDINGS `champion`),
  `src/onboarder/yahoo_client.py`; unit tests for the processor and onboarder.
- **Data**: already-onboarded Yahoo leagues need a refresh or reprocess to pick up the fixes.
  Transaction weeks need a re-onboard or refresh, which fetches the week calendar.
