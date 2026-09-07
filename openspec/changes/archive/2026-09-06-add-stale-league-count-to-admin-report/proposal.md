## Why

The nightly onboarding digest reports total leagues, active leagues (14d), the ESPN/SLEEPER
split, and new onboards, but it gives no visibility into leagues that have gone cold. A league
that has not been refreshed in over a year is a candidate for pruning/archival, and today the
only way to see that count is to run the `flag_stale_espn_leagues.py` utility by hand. Surfacing
a **stale-league count** in the same nightly digest makes this trend visible automatically.

## What Changes

- Add a **Stale (1y)** field to the nightly Discord digest reporting the number of leagues not
  refreshed in over 1 year.
- A league is stale when its `last_refresh_at` — falling back to `onboarded_at` when it has
  never been refreshed — is more than 365 days before the run time. The 365-day boundary is
  exclusive (a league exactly 1 year old is not stale). A league with neither timestamp
  parseable is excluded from the stale count. This matches the staleness convention already used
  by `scripts/utility_scripts/flag_stale_espn_leagues.py`.

## Capabilities

### Modified Capabilities
- `backend/admin-onboarding-report`: the nightly digest additionally reports a stale-league
  count (leagues whose `last_refresh_at`, falling back to `onboarded_at`, is older than 365
  days).

## Impact

- Backend only. No API / DynamoDB schema / infrastructure / architecture-diagram change (same
  Lambda, no new env vars; `last_refresh_at` is already documented and GSI3-projected).
- `src/admin_report/aggregations.py`: new pure `count_stale(items, now, days=365)` helper.
- `src/admin_report/handler.py`: import `count_stale`, add a `STALE_DAYS` constant, and add the
  `Stale (1y)` field to `_build_embed`.
- Tests: `tests/unit/admin_report/test_aggregations.py` (`TestCountStale`) and
  `tests/unit/admin_report/test_handler.py` (assert the new field).
