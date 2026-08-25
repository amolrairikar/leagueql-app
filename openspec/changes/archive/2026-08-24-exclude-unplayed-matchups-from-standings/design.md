## Context

See proposal.md — Why. Unplayed weeks of an in-progress season are already persisted as `0-0`
placeholder matchups (`winner="TIE"`) by the processor (ESPN `src/processor/handler.py:705-713`,
Sleeper `:1010-1018`). Aggregation is split across two tiers: the DuckDB `STANDINGS`/
`WEEKLY_STANDINGS` transforms in `src/processor/queries.py`, and per-feature client-side loops over
the raw `MATCHUPS` view in `frontend/src/features/**`. Both derive W/L/T from score comparison, so a
`0-0` row reads as a tie. All-time standings are summed client-side from per-season
`STANDINGS#{season}`, so fixing the backend transform fixes all-time transitively.

## Goals / Non-Goals

**Goals:**
- Keep storing `0-0` rows (a future live-playoff-odds sim replays the remaining schedule from them).
- Exclude `0-0` unplayed matchups from every standings/stat aggregation, backend and frontend.
- One consistent definition of "unplayed" shared across all consumers.

**Non-Goals:**
- No marker column / schema change on the stored `MATCHUPS` view; no DynamoDB or OpenAPI change.
- No change to raw list display or box-score rendering — the placeholder rows stay visible there.
- No handling of partially-played (in-progress) weeks — only fully-unplayed `0-0` games.
- The playoff-odds feature itself is out of scope (future work).

## Decisions

**Unplayed heuristic = both scores exactly `0`.** A played fantasy game essentially never ends
`0-0` for both teams (scores are fractional), so `team_a_score == 0 && team_b_score == 0` is a
reliable proxy. Chosen over (a) an explicit `is_played`/`status` marker column — rejected as it
touches the DynamoDB spec, OpenAPI, frontend types, and every writer/reader for no added
correctness here; and (b) filtering by current NFL week — rejected as it needs a wall-clock/week
source at processing time and would wrongly drop legitimately empty weeks. A genuine played game
where one team scores `0` is retained because the other side is `> 0`.

**Backend: filter in the `weekly_stats` CTEs, not at write time.** Add
`AND NOT (CAST(team_a_score AS DOUBLE) = 0 AND CAST(team_b_score AS DOUBLE) = 0)` to all four
`WHERE playoff_tier_type = 'NONE'` branches (two in `STANDINGS`, two in `WEEKLY_STANDINGS`).
Excluded weeks produce no rows, so `COUNT(*) OVER (... week)` (all-play denominator),
`RANK() OVER (... points_for)`, `games_played`, `win_pct`, and PF/PA sums/averages all
self-correct. The playoff `champion` CTE reads `WINNERS_BRACKET` and is untouched. The `MATCHUPS`
transform is untouched, so the placeholder rows remain stored.

**Frontend: one shared helper, applied at each aggregation choke point.** Add
`isUnplayedMatchup(m)` in a new `frontend/src/lib/matchups.ts` (the established cross-feature helper
home) and guard each compute loop with it, next to existing playoff/bye guards. Chosen over
per-feature inline checks to keep the definition single-sourced and identical to the backend.

## Risks / Trade-offs

- A real `0-0` tie (astronomically unlikely in fantasy football) would be dropped → accepted;
  the correctness gain for every in-progress season vastly outweighs it, and the same convention
  is applied uniformly so backend and frontend never disagree.
- Missing one client-side consumer would leave a stat inconsistent → mitigated by enumerating all
  raw-`MATCHUPS` consumers up front and covering each with a test asserting exclusion; features
  reading precomputed `STANDINGS`/`WEEKLY_STANDINGS` are covered by the backend fix.
- Display features intentionally keep `0-0` rows → acceptable and desired for the future sim; the
  split (exclude from stats, keep in display) is the whole point of the heuristic-not-filter choice.
