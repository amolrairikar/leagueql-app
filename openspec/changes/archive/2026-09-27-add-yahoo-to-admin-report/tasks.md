# Tasks

## 1. Aggregation

- [x] 1.1 Add `"YAHOO"` to `_PLATFORMS` in `src/admin_report/aggregations.py` and update the module docstring's `platform` enum description (ESPN / SLEEPER / YAHOO)
- [x] 1.2 Update `tests/unit/admin_report/test_aggregations.py::TestPlatformCounts`: expect a `YAHOO` key in the empty result, count a YAHOO league (plus a migrated league), and use a truly unknown platform (e.g. `"FLEAFLICKER"`) in the ignored-platform test. Verify with `pipenv run pytest tests/unit/admin_report/test_aggregations.py`

## 2. Discord embed

- [x] 2.1 Rename the embed field in `src/admin_report/handler.py` to `ESPN / SLEEPER / YAHOO` with value `e / s / y`, and update the module docstring's split wording
- [x] 2.2 Update `tests/unit/admin_report/test_handler.py`: seed a YAHOO league in the digest test, assert the new field name/value (e.g. `"1 / 2 / 1"`), and assert `"0 / 0 / 0"` in the empty case. Verify with `pipenv run pytest tests/unit/admin_report`
- [x] 2.3 Update `tests/component/features/admin_onboarding_report.feature`: add a YAHOO league to the digest scenario, assert the `ESPN / SLEEPER / YAHOO` field in both scenarios, and update the feature description. Reuse the existing platform seed step. Verify with `pipenv run behave tests/component/features/admin_onboarding_report.feature`

## 3. Wrap-up

- [x] 3.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`, then `openspec validate add-yahoo-to-admin-report`. Verify that both pass cleanly
