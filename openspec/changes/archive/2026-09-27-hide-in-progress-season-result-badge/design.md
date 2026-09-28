# Design

## Context

`withInProgressRanks` in `frontend/src/features/manager_history/api-calls.ts` already decides
whether a season is finalized: some team has `final_rank` ≥ 1, where ESPN reports `0` and Sleeper
reports `null` until the season ends. For an unfinalized season it overwrites `final_rank` with a
provisional standings rank, so later code can no longer tell the season is in progress. The
season card's pill is derived from `champion`, the Finals loser, and playoff-bracket
participation, and defaults to "Missed Playoffs".

## Decisions

- **Reuse the existing finalized test and carry it forward as `in_progress`.**
  `withInProgressRanks` sets `in_progress: true` on every row of an unfinalized season,
  including seasons with no games played yet. Recomputing the check in the component would
  duplicate logic and could drift.
- **Hide the pill rather than add an "In progress" pill.** This follows the request to stop
  showing a result for the current season. `SeasonEntry.result` becomes `null` for such seasons,
  and the badge is not rendered. The champion border already keys off `result === 'champion'`,
  so it stays off.
- **Hide the pill until the season is finalized, not just until playoffs start.** Sleeper leaves
  `final_rank` null until the bracket resolves, so there is no reliable, platform-neutral signal
  for "regular season over, playoff field set" in this view. Hiding it for the whole in-progress
  season is simpler and never shows a wrong result.

## Non-Goals

- The all-time "Playoffs" and "Championships" counts are unchanged. Both come only from real
  playoff games or `champion = "Yes"`, so they don't produce false outcomes.
