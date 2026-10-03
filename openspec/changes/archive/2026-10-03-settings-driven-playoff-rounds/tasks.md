# Tasks

## 1. Playoff structure from league settings

- [x] 1.1 Add `playoff_week_start_assumed` to `build_league_settings_row` (true when the default start week was used), and strip it before the `LEAGUE_SETTINGS` item is written; verify with unit tests in `tests/unit/processor/test_pure_functions.py` that the flag is set correctly and that the written item's keys are unchanged
- [x] 1.2 Add a `playoff_structure(settings_row)` helper returning `(first_week, total_rounds)` using `ceil(log2(num_playoff_teams))`, or `None` when either value is assumed or the team count is < 2; verify with unit tests covering 4 teams/start 14 → (14, 2), 6 teams/start 15 → (15, 3), assumed start, assumed team count, and a count of 1
- [x] 1.3 Add an observed-weeks fallback helper that, given one season's winners-bracket weeks and game counts, returns per-week `round_num` and `total_rounds` (counted back when the last week has exactly one game, `total_rounds = None` otherwise); verify with unit tests for a completed 2-week season, a completed 3-week season, and an in-progress season with a single 2-game week

## 2. Round numbers on matchup rows and round labels

- [x] 2.1 In the ESPN and Yahoo raw-data registration, set `playoff_round_num` / `playoff_total_rounds` on each winners-bracket matchup from the settings structure (`week - first_week + 1`), falling back to 1.3 when there's no structure or a round falls outside `1..total_rounds` (log a warning); verify with unit tests for a 13-period / 4-team / two-week-round ESPN season (period 14 → round 1, period 15 → round 2 of 2) and a defaulted-settings season
- [x] 2.2 In the Sleeper raw-data registration, set the same fields from the matched bracket entry's `r` and the winners bracket's max `r`; verify with a unit test that a matchup pairing a round-2 match's teams in a 3-round bracket gets round 2 of 3
- [x] 2.3 Replace both hardcoded `playoff_round` CASE blocks in `src/processor/queries.py` with the shared mapping on `playoff_total_rounds - playoff_round_num` (Finals/Semifinals/Quarterfinals/`Round N`), keeping the Winners Consolation / Losers Bracket labels; register the new columns in `_EMPTY_VIEW_DTYPES` if needed; verify with unit tests in `tests/unit/processor/test_handler.py` that run the MATCHUPS transform on synthetic ESPN, Yahoo and Sleeper rows and assert the labels from the spec scenarios ("Final played before week 17", "Labels before the final is played", "Sleeper labels follow bracket rounds", "Non-winners tiers keep their labels")
- [x] 2.4 Update the `playoff_round` row in `docs/db/dynamodb_spec.md` to describe the settings-derived labels and the `Round N` fallback value; verify the doc no longer mentions fixed weeks

## 3. Bracket rounds and placements

- [x] 3.1 Change `_build_espn_brackets` to take `round` from `playoff_round_num` and to assign placements (`position` 1/3/5) only when `round == playoff_total_rounds` (none when that is `None`); verify with unit tests that a semifinal-only bracket has round 1 and no `position = 1`, that the completed bracket has the final at round 2 with `position = 1`, that a 6-team bracket with byes keeps null `team_*_from` for bye teams, and that existing Yahoo placement/consolation tests still pass

## 4. Champion from the labeled final

- [x] 4.1 Replace the `winners_bracket_weeks` / `champion` CTEs in `QUERIES["STANDINGS"]` with the decided winners-bracket "Finals" winner (latest week if more than one); verify with unit tests for exactly one champion in a completed season, a final in matchup period 15, and no champion when only the semifinals are played (or the final is a 0–0 placeholder)
- [x] 4.2 Add a Behave scenario to `tests/component/features/onboard_to_processed.feature` (with steps) for an ESPN league with 4 playoff teams and two-week rounds whose final is matchup period 15: assert the period-15 game's `playoff_round` is "Finals", the period-14 games are "Semifinals", the standings name the final's winner (a generic team such as "Team A") as the only champion, and the bracket has exactly one `position = 1` match; verify with `pipenv run behave tests/component`
- [x] 4.3 Update `openspec/specs` wording only through this change's deltas (no direct edits); verify with `npx @fission-ai/openspec@latest validate settings-driven-playoff-rounds --strict`

## 5. Frontend: Manager Comparison and Manager History

- [x] 5.1 Add a STANDINGS fetch (the same `SEASON_STANDINGS#` prefix query Manager History uses, with a no-data `404` treated as no rows) to `frontend/src/features/manager_comparison/api-calls.ts`, loaded in parallel with matchups; verify with MSW-mocked scenarios in `manager-comparison.feature` that the page still renders when standings 404, and that a standings `5xx` surfaces through the app error boundary (the feature has no inline error state; a matchups `5xx` already behaves this way)
- [x] 5.2 Count championships from STANDINGS rows with `champion === 'Yes'` keyed by the migration-mapped `owner_id`, removing the `playoff_round === 'Finals'` scan; verify with a new `manager-comparison.feature` scenario where a manager's team is marked `champion = Yes` in the mocked STANDINGS while none of the mocked matchups is labeled "Finals", and the manager shows one championship (no existing scenario covered championships)
- [x] 5.3 Add a `manager-history.feature` scenario ("Runner-up of an early final") where the losing team of a period-15 "Finals" game in a finalized season shows the "Runner-up" pill and 2nd-place finish; verify with `npx vitest run src/features/manager_history`
- [x] 5.4 Run `npm run format:fix`, `npm run lint`, and `npx vitest run src/features/manager_comparison src/features/manager_history src/features/matchups src/features/playoff_bracket` from `frontend/`; verify all pass

## 6. Integration checks

- [x] 6.1 Run `pipenv run ruff check --fix .`, `pipenv run ruff format .`, `pipenv run pytest tests/unit`, and `pipenv run behave tests/component`; verify everything passes and processor coverage stays near 100%
- [x] 6.2 Run the full processor transforms locally on a synthetic multi-season ESPN fixture (one season with two-week rounds ending in period 15, one with one-week rounds ending in week 17, one in progress) and verify labels, bracket placements and champions match the spec scenarios
