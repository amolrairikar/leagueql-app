## 1. Backend transform

- [x] 1.1 In `src/processor/queries.py`, add `AND NOT (CAST(team_a_score AS DOUBLE) = 0 AND CAST(team_b_score AS DOUBLE) = 0)` to all four `WHERE playoff_tier_type = 'NONE'` branches (two in `STANDINGS`, two in `WEEKLY_STANDINGS`); leave the `MATCHUPS` and `champion` queries unchanged.
- [x] 1.2 Add a backend component scenario in `tests/component/features/onboard_to_processed.feature` (+ a Sleeper fixture variant with an unplayed `0-0` week) asserting `STANDINGS#{season}`/`WEEKLY_STANDINGS#{season}` exclude the unplayed week while its `MATCHUPS#{season}#WEEK#{week}` item is still written; verify `pipenv run behave tests/component` passes.
- [x] 1.3 Run `pipenv run pytest tests/unit/processor` and confirm existing processor unit tests still pass.

## 2. Frontend shared helper

- [x] 2.1 Add `frontend/src/lib/matchups.ts` exporting `isUnplayedMatchup(m: MatchupItem): boolean` (both scores exactly `0`); add `frontend/src/lib/__tests__/matchups.test.ts` (vitest) and verify it passes.

## 3. Frontend aggregation guards

- [x] 3.1 `weekly_awards/compute-awards.ts`: return `null` from `sides()` for unplayed matchups; add a vitest case in `__tests__/compute-awards.test.ts` proving a `0-0` game wins no award and doesn't affect tallies/streaks.
- [x] 3.2 `schedule_swap/compute-schedule-swap.ts`: skip unplayed matchups at the ingest loop; add a vitest case in `__tests__/compute-schedule-swap.test.ts` proving simulated records exclude them.
- [x] 3.3 `season_standings/compute-sos.ts`: skip unplayed matchups beside the `isRegularSeason` guard; add a vitest case in `__tests__/compute-sos.test.ts` proving no phantom opponents.
- [x] 3.4 `matchup_records/matchup-records.tsx`: skip unplayed matchups in `extractRecords`; update the jest-cucumber pair to assert a `0-0` game never surfaces on a record board.
- [x] 3.5 `manager_comparison/manager-comparison.tsx`: skip unplayed matchups in both `buildManagers` and `buildGameLogs`; update the jest-cucumber pair to assert exclusion from records and game log.
- [x] 3.6 `manager_history/manager-history.tsx`: skip unplayed matchups in the `processData` matchups loop; update the jest-cucumber pair to assert exclusion.
- [x] 3.7 `home_page/home-page.tsx`: skip unplayed matchups in `buildAllTimeStandings` and `computeTotalGames`; update the jest-cucumber pair to assert exclusion.
- [x] 3.8 `player_records/player-records.tsx`: skip unplayed matchups in `extractEntries`; update the jest-cucumber pair to assert exclusion from player score boards.

## 4. Quality gates

- [x] 4.1 Backend lint/format: `pipenv run ruff check --fix .` and `pipenv run ruff format .`.
- [x] 4.2 Frontend (from `frontend/`): `npm run format:fix`, `npm run lint`, and `npx vitest run` on the touched `src/features/**/__tests__` and `src/lib/__tests__` paths — all green.
- [x] 4.3 `npx @fission-ai/openspec@latest validate --all` passes.
