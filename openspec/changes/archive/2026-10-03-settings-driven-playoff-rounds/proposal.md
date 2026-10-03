# Proposal

## Why

Playoff round labels (`playoff_round`) on the ESPN and Yahoo matchups views come from fixed week
numbers (weeks 15/16/17 from 2021 on, 14/15/16 before). A league with a different playoff schedule
gets the wrong labels. One example is an ESPN league with 13 regular-season matchup periods, a
4-team playoff and two-week rounds: its semifinal is matchup period 14 and its final is period 15.
That league's semifinals get no label, its title game is labeled "Quarterfinals", and no game is
ever labeled "Finals". Manager Comparison counts championships only from `'Finals'` wins, so it
shows zero titles for every manager. Manager History uses the same label to find runners-up, so it
never shows one.

The ESPN/Yahoo bracket builder has a related weakness. It numbers rounds by the playoff weeks it
has seen so far and treats the last one as the championship. During the playoffs, that can mark a
semifinal as the title game. The league settings already describe the full playoff structure
(first playoff week and number of playoff teams), so rounds should come from them.

## What Changes

- The processor works out each season's playoff structure from its league settings: the first
  playoff week, the number of rounds (`ceil(log2(num_playoff_teams))`), and the final week. It
  uses this only when both values came from the platform rather than from defaults.
- ESPN and Yahoo `playoff_round` labels are counted back from that final week (Finals,
  Semifinals, Quarterfinals, …) instead of read from fixed week numbers. Sleeper labels come from
  the round number Sleeper puts on each bracket match.
- When a season's settings were defaulted, labels fall back to the observed winners-bracket weeks:
  counted back from the last week once that week holds a single title game, and numbered forward
  ("Round N") while the playoffs are still in progress.
- The ESPN/Yahoo `PLAYOFF_BRACKET` builder takes round numbers from the settings-derived structure
  and assigns final placements (`position` 1/3/5) only to games in the final round, never to the
  latest round seen so far.
- The STANDINGS `champion` flag is the winner of the decided winners-bracket game labeled
  "Finals", so the champion, round labels and bracket all use one definition of the final.
- Manager Comparison counts championships from the STANDINGS `champion` flag instead of
  recomputing them from `playoff_round === 'Finals'`. Manager History identifies the runner-up as
  the loser of the decided winners-bracket "Finals" game, which is now correctly labeled.
- No stored schema changes: `playoff_round`, bracket fields and `champion` keep their shapes.
  Reprocessing a league (`reprocess_all`) corrects its stored views.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/data-processing-pipeline`: adds requirements for settings-driven playoff round labels
  and settings-driven ESPN/Yahoo bracket rounds and placements; changes "Determine a single
  champion per season" to use the labeled final.
- `frontend/manager-comparison`: championships come from the STANDINGS `champion` flag rather
  than from Finals labels on matchups.
- `frontend/manager-history`: adds a requirement that the runner-up is the loser of the season's
  title game.

## Impact

- **Backend:** `src/processor/handler.py`: the ESPN/Yahoo/Sleeper raw-data registration
  (playoff structure per season, Sleeper bracket round per matchup), `_build_espn_brackets`
  (shared by Yahoo), `build_league_settings_row` (tracking which values were defaulted).
  `src/processor/queries.py`: the `MATCHUPS` `playoff_round` CASE blocks (ESPN/Yahoo and
  Sleeper) and the `STANDINGS` champion CTE.
- **Frontend:** `frontend/src/features/manager_comparison/` (also fetches STANDINGS per season;
  championship counting). Manager History and the Matchups page need no code change beyond
  receiving correct labels. The playoff-bracket page's score-to-week join stays valid because
  rounds still run 1..k with the latest observed round in the latest playoff week.
- **Tests:** processor unit tests, the onboard→processed Behave component scenario, and the
  manager-comparison / manager-history jest-cucumber features.
- **Data:** existing leagues keep their old labels until reprocessed. No migration script; a
  reprocess (or the next refresh, for the latest season) rewrites the views.
- **Docs:** `docs/db/dynamodb_spec.md` wording for `playoff_round` / `champion` if it describes
  the fixed-week rule. No API contract change.
