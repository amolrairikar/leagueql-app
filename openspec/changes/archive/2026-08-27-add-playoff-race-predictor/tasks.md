## 1. Backend — LEAGUE_SETTINGS view

- [x] 1.1 Add a `LEAGUE_SETTINGS` `EntityType` and its key schema (`SK = LEAGUE_SETTINGS#{season}`) in `src/processor/handler.py` near the existing `PLAYOFF_BRACKET` definitions; verify the enum and key-schema registration import without error (`pipenv run python -c "import src.processor.handler"`).
- [x] 1.2 In the Sleeper pre-pass (`src/processor/handler.py` ~L973–980), extract `num_playoff_teams` from `settings.playoff_teams` and `playoff_week_start` from `settings.playoff_week_start`; derive `regular_season_weeks = playoff_week_start - 1`; default `playoff_week_start` to 15 (season ≥ 2021) else 14 when absent, and `num_playoff_teams` to 6 when absent. Verify with a unit test over a Sleeper settings fixture.
- [x] 1.3 In the ESPN settings branch (`src/processor/handler.py` ~L694–698), extract `num_playoff_teams` from `settings.scheduleSettings.playoffTeamCount` and `regular_season_weeks` from `matchupPeriodCount`; set `playoff_week_start = matchupPeriodCount + 1`; default `num_playoff_teams` to 6 when absent. Verify with a unit test over an ESPN settings fixture.
- [x] 1.4 Write the `LEAGUE_SETTINGS#{season}` item (fields: `season`, `num_playoff_teams`, `playoff_week_start`, `regular_season_weeks`) per season alongside the other view writes, idempotently. Verify a processor unit test asserts the item is written for both platforms.
- [x] 1.5 Add processor unit tests under `tests/unit/processor/` for the missing-setting → default-6 path (both platforms); run `pipenv run pytest tests/unit/processor`.

## 2. Backend — expose via query endpoint

- [x] 2.1 Add `LEAGUE_SETTINGS` to the `QueryType` enum + `QUERY_TYPE_TO_SK_BASE` in `src/api/routes.py`; verify `GET /leagues/{id}/query?queryType=LEAGUE_SETTINGS#{season}` resolves to the right SK.
- [x] 2.2 Add a `tests/component/` scenario asserting `queryType=LEAGUE_SETTINGS#{season}` returns the persisted `num_playoff_teams`/`playoff_week_start`/`regular_season_weeks` through moto DynamoDB; run `pipenv run behave tests/component`.
- [x] 2.3 Update `docs/api/openapi_spec.yaml` `queryType` enum and add the `LEAGUE_SETTINGS` item to `docs/db/dynamodb_spec.md`; verify both files reference the new view consistently.

## 3. Frontend — projection core

- [x] 3.1 Add `LeagueSettingsItem` to `frontend/src/components/api/types.ts` and `getLeagueSettings(leagueId, platform, season)` in the new `frontend/src/features/playoff_race_predictor/api-calls.ts`; verify it type-checks (`npm run build` or `tsc`).
- [x] 3.2 Export `isRegularSeason` from `frontend/src/features/schedule_swap/compute-schedule-swap.ts` and import it in `compute-sos.ts` (drop the duplicate); verify existing schedule-swap and SoS tests still pass.
- [x] 3.3 Implement `compute-projection.ts` (pure): build team roster + baseline records/PF from `MATCHUPS`; mode-aware pickable weeks (`live` = unplayed reg weeks bounded by `regular_season_weeks`; `replay` = last 3 reg weeks); `recordEnteringWeek`, pick-driven projection, sort (wins desc then PF desc), cutoff at `num_playoff_teams`, movement vs baseline, clinched flag. Verify `compute-projection.test.ts` covers both modes and the clinch/movement logic.

## 4. Frontend — predictor UI

- [x] 4.1 Build `playoff-race-predictor.tsx` to the locked mockup (week stepper, click-to-pick cards showing record entering the week, reset, live-re-sorting projected standings with the dashed playoff line + "assumed" note, movement/clinch indicators); fetch matchups + league settings via `Promise.all` + `toResult` under Suspense. Verify it renders against MSW fixtures.
- [x] 4.2 Self-gate: render the tool only when ≥1 pickable regular-season week exists and no played playoff matchup; otherwise render the existing empty message. Verify a step test for the not-in-progress case.

## 5. Frontend — wire into the bracket page

- [x] 5.1 In `playoff-bracket.tsx` empty-state branch, render `<PlayoffRacePredictor mode="live" …/>` when `selectedSeason` is the latest season, else keep `PLAYOFF_EMPTY_MESSAGE`. Verify the delegation with a playoff-bracket step test (in-progress fixture → predictor; past season → message).
- [x] 5.2 In the bracket-present branch, when `isDemoMode()`, render a `Bracket / Playoff Race` segmented toggle; `Playoff Race` swaps the grid for `<PlayoffRacePredictor mode="replay" …/>`. Verify non-demo bracket rendering is unchanged.

## 6. Demo data

- [x] 6.1 In `scripts/utility_scripts/seed_demo_data.py` emit a `LEAGUE_SETTINGS#{season}` row per season (`num_playoff_teams=4`, `playoff_week_start=16`, `regular_season_weeks=15`); add `LEAGUE_SETTINGS → LEAGUE_SETTINGS` to `QUERY_TYPE_TO_SK_BASE` in `frontend/src/lib/demo-api.ts`.
- [x] 6.2 Regenerate `frontend/src/lib/demo-data.json` (`pipenv run python scripts/utility_scripts/seed_demo_data.py`); verify the diff adds only `LEAGUE_SETTINGS` buckets and update any demo-data shape assertions.

## 7. Tests & docs

- [x] 7.1 Add jest-cucumber `*.feature` + `*.steps.test.tsx` for the predictor (live renders for in-progress season; pick re-sorts + crosses the playoff line; reset; empty message when reg season complete / a playoff game played; only latest season shows the live predictor). Run `npx vitest run frontend/src/features/playoff_race_predictor`.
- [x] 7.2 Extend `frontend/src/features/demo/__tests__/demo-mode.feature` with the demo toggle scenario and add a delegation scenario to the existing `playoff-bracket` feature; run the affected suites.
- [x] 7.3 Lint/format both stacks: `pipenv run ruff check --fix . && pipenv run ruff format .`; from `frontend/`, `npm run lint && npm run format:fix`.

## 8. Verification

- [x] 8.1 `openspec validate --all` is green.
- [x] 8.2 Full test pass: `pipenv run pytest`, `pipenv run behave tests/component`, and `npx vitest run` from `frontend/` all pass.
- [ ] 8.3 Manual (`/run` or dev server): in-progress season → live predictor picks re-sort standings, line/movement/clinch update, records show entering each week, reset restores baseline; completed season → bracket unchanged; demo → toggle replays weeks 13–15; light/dark both read correctly.
