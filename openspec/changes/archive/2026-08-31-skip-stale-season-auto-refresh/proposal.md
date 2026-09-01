## Why

The scheduled Sleeper auto-refresher refreshes the newest onboarded season's league ID for
each canonical league, with no check that the league has been onboarded for the *current* NFL
season. After a season rollover (e.g. 2025 → 2026), a league not yet re-onboarded for the new
season keeps re-refreshing its completed prior season every cycle — wasted Sleeper API calls,
onboarder invocations, and DynamoDB/S3 writes for data that cannot change (Sleeper links
seasons backward-only, so the old ID can never discover the new season).

## What Changes

- The auto-refresher skips any canonical league whose newest onboarded season is **behind** the
  current NFL season, and skips stale pending renewal lookups whose `pending_season` is behind
  the current NFL season. Leagues at (or ahead of) the current season refresh as before.
- The handler now raises when NFL state lacks a parseable `season`, treating it as indeterminate
  state rather than mass-refreshing/misclassifying.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `backend/scheduled-sleeper-auto-refresh`: refresh selection is gated on the current NFL
  season — leagues (and pending renewals) whose season is behind the current NFL season are
  skipped; indeterminate NFL state now includes a missing/unparseable `season`.

## Impact

- Code: `src/sleeper_refresh/utils.py` (`get_sleeper_leagues` gains a `current_season` arg),
  `src/sleeper_refresh/handler.py` (extracts/validates `season`, passes it through).
- Tests: `tests/unit/sleeper_refresh/`, `tests/component/features/sleeper_auto_refresh.feature`
  and its steps.
- No infrastructure, API contract, or DynamoDB item-shape changes.
