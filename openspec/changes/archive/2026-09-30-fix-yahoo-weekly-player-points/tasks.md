# Tasks

## 1. Onboarder

- [x] 1.1 Store `num_teams` in each resolved season's metadata.
- [x] 1.2 Build one weekly roster+stats URL per team (`rosters_week{W}_t{t}`); skip with a warning when `num_teams` is unknown.
- [x] 1.3 Parse the single-team roster payload in `_filter_rosters`.
- [x] 1.4 Merge per-team roster results into one `rosters_week{W}` record per season/week.

## 2. Tests & quality

- [x] 2.1 Onboarder unit tests: real single-team fixture, per-team URLs, missing `num_teams`, merge.
- [x] 2.2 Run ruff, pytest, behave, and `openspec validate --all`.
