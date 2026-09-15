## 1. Implement played-week detection

- [x] 1.1 In `src/api/helpers.py`, rework `get_latest_stored_matchup` to return the latest **played** stored week: query `MATCHUPS#` items with `ScanIndexForward=False`, project `SK` and `data`, walk items newest-first, and return the `(season, week)` of the first item whose `data` has any row with `team_a_score > 0` or `team_b_score > 0`; paginate via `ExclusiveStartKey`; return `None` when no stored week is played. Verify by reading the updated helper and confirming the docstring documents the played-week semantics.
- [x] 1.2 Confirm the refresh guard in `src/api/routes.py` needs no logic change (it already compares the helper's `(season, week)` to NFL state) and that its comment/behavior still reads correctly given the new "latest played" semantics.

## 2. Backend unit tests

- [x] 2.1 In `tests/unit/api/test_endpoints.py`, add/adjust `get_latest_stored_matchup` tests: (a) a league whose newest stored weeks are unplayed (0–0, `winner "TIE"`) returns the earlier played `(season, week)`; (b) a fully played league returns its max week (unchanged behavior); (c) a league whose only stored week(s) are unplayed returns `None`; (d) empty/no matchups returns `None`. Verify with `pipenv run pytest tests/unit/api/test_endpoints.py`.
- [x] 2.2 Run `pipenv run pytest tests/unit` and confirm coverage of the new branch(es) in `get_latest_stored_matchup` (played-detection and pagination paths) stays near 100%.

## 3. Backend component tests

- [x] 3.1 In `tests/component/features/league_refresh.feature` (+ its steps), add a scenario: an ESPN league that is behind current NFL state but already has later unplayed weeks stored is allowed to refresh (`201`), and confirm the existing "genuinely current league → `409`" scenario still passes. Verify with `pipenv run behave tests/component/features/league_refresh.feature`.

## 4. Quality gate and spec validation

- [x] 4.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`; confirm no lint/format errors remain.
- [x] 4.2 Run `openspec validate fix-espn-refresh-played-week-guard --strict` and confirm it passes.
