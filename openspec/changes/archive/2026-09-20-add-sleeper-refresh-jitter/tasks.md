## 1. Dispatcher jitter

- [x] 1.1 In `src/sleeper_refresh/handler.py`, add `import random` and `import time` and read `REFRESH_JITTER_WINDOW_SECONDS` (default `600`, coerced to a number, `0` = disabled) at dispatch time
- [x] 1.2 Before the dispatch loop, when the window is `> 0` and there is more than one league, draw a `random.uniform(0, window)` offset per league, sort ascending, and iterate in that order sleeping the delta between consecutive offsets (first sleep = smallest offset) before entering each league's trace span; single-league / window-`0` runs dispatch immediately with no sleep. Verify the added logic keeps every league dispatched and the raise-after-loop-on-failure behavior intact

## 2. Infrastructure

- [x] 2.1 In `infrastructure/regional/main.tf` `module "sleeper_refresh_lambda"`, bump `timeout` 60 → 900 and add `REFRESH_JITTER_WINDOW_SECONDS = "600"` to `environment_variables`, with a comment tying the timeout to the window. Verify `terraform plan` shows only the timeout change and the new env var (no other resource churn)

## 3. Tests

- [x] 3.1 Update `tests/unit/sleeper_refresh/test_handler.py`: patch `time.sleep` (or set the window to `0`) so tests never actually sleep; keep existing cases green (skip off-season/week-1, raise on NFL-state/query failure, raise-after-loop on dispatch failure). Verify `pipenv run pytest tests/unit/sleeper_refresh` passes
- [x] 3.2 Add unit cases for the jitter branches: (a) window > 0 with >1 league → `time.sleep` is called, summed sleep ≤ window, all leagues dispatched, order randomized; (b) window `0` or single league → no sleep, immediate dispatch. Verify coverage stays ~100% including the new branch
- [x] 3.3 Ensure `tests/component/features/sleeper_auto_refresh.feature` + steps run with the window at `0` (deterministic, no real sleep) and still assert every selected league's onboarder is invoked. Verify `pipenv run behave tests/component` passes

## 4. Validation

- [x] 4.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`; verify clean
- [x] 4.2 Run `openspec validate add-sleeper-refresh-jitter --strict`; verify it passes
