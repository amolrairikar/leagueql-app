# Proposal

## Why

Yahoo leagues can now be onboarded, but the nightly Discord onboarding report only splits leagues
into ESPN and SLEEPER. Yahoo leagues are counted in the total, active, stale, and new-onboard
numbers but left out of the platform split, so ESPN + SLEEPER no longer adds up to the total and
there is no way to see how many Yahoo leagues exist.

## What Changes

- The platform split in the nightly digest covers ESPN, SLEEPER, **and YAHOO**.
- The Discord embed field changes from `ESPN / SLEEPER` (`e / s`) to `ESPN / SLEEPER / YAHOO`
  (`e / s / y`). The field name changes, so anything reading the old field name would break.
  Only people read this message, so the rename is not treated as a breaking change.
- A league whose effective platform is anything else (or missing) is still left out of the split.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/admin-onboarding-report`: the "Nightly onboarding-health digest" requirement reports
  an ESPN / SLEEPER / YAHOO split instead of ESPN-vs-SLEEPER.

## Impact

- `src/admin_report/aggregations.py`: `_PLATFORMS` gains `YAHOO`, and the module docstring is updated.
- `src/admin_report/handler.py`: the embed field is renamed and gets a third value. The module
  docstring is updated too.
- Tests: `tests/unit/admin_report/` (`test_aggregations.py`, `test_handler.py`) and
  `tests/component/` (`admin_onboarding_report.feature`, `admin_report_steps.py`).
- No changes to infrastructure, the API, the data model, or the frontend.
