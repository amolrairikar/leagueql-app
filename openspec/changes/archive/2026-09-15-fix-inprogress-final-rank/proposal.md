## Why

On `/home` the "Final standings position by season" chart plots every owner at rank `0`
for an in-progress season (e.g. one week completed). ESPN reports a team's
`rankCalculatedFinal` — the source of `final_rank` in the `SEASON_STANDINGS#` view — as
`0` until the season is finalized (Sleeper leaves it `null` until its playoff bracket
resolves), and the processor passes that through (`src/processor/queries.py`). The shared
fetch `getManagerHistoryData` (`frontend/src/features/manager_history/api-calls.ts`)
returns `final_rank: 0`, so:

- the home standings-position chart draws a point at rank `0` (off/at the top of the
  reversed axis) and the tooltip shows "0" for the in-progress season, and
- `/manager_history` shows "0th place" (via `final_rank ?? null`, where `0` is not
  nullish) instead of a meaningful finish for that season.

Rank `0` is not a valid placement — ranks start at `1` — it means "not finalized yet".
An in-progress season does, however, have a meaningful *current* standings position
derived from the regular-season record, which is what these views should show.

## What Changes

- At the shared fetch boundary (`getManagerHistoryData`), fill in `final_rank` for an
  in-progress season from the current standings instead of leaving a bogus `0`. A season
  where **no** team has a finalized placement (all `0`/`null`) and at least one game has
  been played is treated as in-progress: each team's `final_rank` is set to its current
  standings position, ordered by **wins, then points-for** — the same canonical order the
  backend `SEASON_STANDINGS` view uses (`ORDER BY ... wins DESC, total_pf DESC`).
  - Finalized seasons are unchanged (real `final_rank` per team; Sleeper non-playoff
    teams keep their `null`).
  - A season with no games played yet keeps a `null` `final_rank` (nothing to rank), and
    any residual non-positive `final_rank` is normalized to `null` so it is never plotted
    at rank `0`.
- Both consumers then show the in-progress season correctly: the home chart's line
  continues to the current position, and `/manager_history` shows that season's current
  standings position as its finish.
- Add a `/manager_history` component scenario for the in-progress case. This exercises the
  shared `getManagerHistoryData` logic that also feeds the home standings-position chart;
  the chart is SVG-only (no reliable DOM assertion in JSDOM), so the same computed output
  is verified through the manager-history finish text.

No API, DynamoDB, or backend behavior changes — this derives a client-side current
standings position for an unfinalized season from fields already in the
`SEASON_STANDINGS` view.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `frontend/home-dashboard`: the standings-position chart plots an in-progress season at
  its current standings position (wins, then points-for) rather than at rank `0`.
- `frontend/manager-history`: an in-progress season shows its current standings position
  as the season finish, not "0th place".

## Impact

- `frontend/src/features/manager_history/api-calls.ts` — `getManagerHistoryData` derives
  a current-standings `final_rank` for an in-progress season on read (helper
  `withInProgressRanks`).
- `frontend/src/features/manager_history/__tests__/` — scenario + steps for an in-progress
  season showing its current standings position, covering the shared logic that also feeds
  the home standings-position chart.
- No changes to `src/processor/queries.py` or any backend/data contract.
