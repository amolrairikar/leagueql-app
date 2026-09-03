## 1. Fix null lineup handling

- [x] 1.1 In `compile_sleeper_starter_stats` (`src/processor/handler.py`), coerce `starters` and `starters_points` to empty lists when null, so `zip(...)` no longer raises on a null lineup field
- [x] 1.2 In `compile_sleeper_bench_stats` (`src/processor/handler.py`), coerce `players` to an empty list and `players_points` to an empty dict when null, so iteration and `.get(...)` no longer raise

## 2. Tests

- [x] 2.1 Add unit tests in `tests/unit/processor/test_pure_functions.py` for `compile_sleeper_starter_stats` with null `starters` and null `starters_points`, asserting an empty stats list and empty ids rather than an error
- [x] 2.2 Add unit tests for `compile_sleeper_bench_stats` with null `players` and null `players_points`, asserting an empty result rather than an error
- [x] 2.3 Run `pipenv run pytest tests/unit/processor/test_pure_functions.py` and verify all tests pass

## 3. Quality gates

- [x] 3.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .` and verify no lint/format errors remain
- [x] 3.2 Run `openspec validate fix-sleeper-null-lineup-crash --strict` and verify the change validates
