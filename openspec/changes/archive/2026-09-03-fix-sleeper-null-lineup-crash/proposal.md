## Why

The processor crashes with `TypeError: 'NoneType' object is not iterable` when a Sleeper matchup entry carries a `null` lineup field (`starters`, `starters_points`, `players`, or `players_points`) rather than omitting it. Sleeper emits `null` here for teams with no lineup set in a given week (e.g. a bye, an incomplete roster, or a not-yet-played week), so any refresh that pulls such a week fails the whole run and writes a `FAILED` job status — the user's dashboard never builds.

## What Changes

- Coerce `null` lineup lists to empty in `compile_sleeper_starter_stats` (guards the `zip(starters, starters_points)` crash) and `compile_sleeper_bench_stats` (guards the `for player_id in players` and `players_points.get(...)` crashes).
- The processor treats a `null` lineup field the same as an absent/empty one: the team simply contributes no starter/bench stat rows for that matchup, and the run completes without erroring.
- Add backend unit tests covering `null` `starters`/`starters_points`/`players`/`players_points`.

No breaking changes; this only broadens input tolerance.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/data-processing-pipeline`: extend the existing "Tolerate empty and absent inputs" requirement to also tolerate `null` (not just absent) Sleeper matchup lineup fields.

## Impact

- Code: `src/processor/handler.py` — `compile_sleeper_starter_stats`, `compile_sleeper_bench_stats`.
- Tests: `tests/unit/processor/test_pure_functions.py`.
- No API, DynamoDB schema, or infrastructure changes.
