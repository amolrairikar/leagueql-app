## Context

See `proposal.md` — Why. The refresh up-to-date guard in `src/api/routes.py` calls
`get_latest_stored_matchup(canonical_league_id)` (`src/api/helpers.py:139`) and blocks with
`409` when that `(season, week)` is `>=` current Sleeper NFL state. Today the helper returns
the lexicographically largest `MATCHUPS#{season}#WEEK#{week:02d}` SK (via
`ScanIndexForward=False, Limit=1, ProjectionExpression="SK"`).

Each week is stored as a single item `{PK, SK, data: [<matchup rows>]}` where every row
carries `team_a_score`, `team_b_score`, and `winner` (ESPN and Sleeper produce the same
column names). ESPN writes a row for every scheduled week of the season, including future
ones, where both scores are `0.0` and `winner` is `"TIE"` (the 0 == 0 branch of the
processor). Sleeper only ever writes weeks it fetched, which are played.

## Goals / Non-Goals

**Goals:**
- The up-to-date guard reflects the latest *played* week, so an ESPN league behind current
  NFL state can refresh even though later, unplayed weeks are already stored.
- Keep the change confined to the read path — no change to stored data, other views, or the
  API contract.

**Non-Goals:**
- Not filtering unplayed weeks at write time (Option A). ESPN keeps storing its full-season
  schedule; downstream views are untouched.
- Not changing the cooldown, concurrency, offseason, or owner-gating behavior of the guard.

## Decisions

**Detect "played" by score, not by `winner`.** A stored week counts as played when any of
its `data` rows has `team_a_score > 0` or `team_b_score > 0`. `winner` alone is ambiguous:
an unplayed ESPN week is `0–0 → "TIE"`, indistinguishable by name from a genuine tie — but a
genuine tie has non-zero scores. A fantasy matchup that has actually been played always has
positive scores (even a bye's single team scores), so score-based detection is unambiguous
and platform-agnostic. Sleeper is unaffected: all its stored weeks are played, so its latest
played week equals its latest stored week (today's behavior).

**Rework `get_latest_stored_matchup` to walk newest-first until a played week is found.**
Replace the `Limit=1, ProjectionExpression="SK"` query with a descending query that also
projects `data`, iterate items newest-first, and return the `(season, week)` of the first
item whose `data` shows a played result. Return `None` if no stored week is played (a
league whose only stored matchups are all unplayed — e.g. a brand-new ESPN season before
week 1 completes — which correctly lets the refresh proceed). Paginate with
`ExclusiveStartKey` so the scan is not silently truncated. Alternatives considered:
- *Store a "latest played week" marker at processing time* — cleaner reads, but adds a
  write-side data-model change, widening scope beyond Option B.
- *Derive from WEEKLY_STANDINGS/STANDINGS* — those views may themselves include unplayed ESPN
  weeks; reading matchup bodies is the direct, verifiable signal.

**Bound the read.** A season has ≤18 weeks and all prior seasons are fully played, so the
first played item is reached within at most ~18 items (the current season's trailing unplayed
weeks). Use a modest page size and stop at the first played item; typical cost is a single
query page.

## Risks / Trade-offs

- **Heavier read than projecting only `SK`.** → We now read `data` for up to ~18 small items
  in the worst case (season start). Acceptable for a single guard check on a low-frequency
  endpoint; we stop at the first played item.
- **A season stored with zero played weeks returns `None`.** → Intended: with nothing played
  yet, the guard must not report the league current, so the refresh proceeds. Matches the
  existing "no matchups → `None` → not blocked" contract.
- **Assumes played matchups always have a positive score.** → True for fantasy football
  scoring; a 0–0 real result is not achievable. Documented in code.

## Migration Plan

Pure read-path change; no data migration, no backfill. Deploy the API Lambda. Rollback is
reverting the helper — the old behavior returns immediately. Existing ESPN leagues start
refreshing correctly on the next request with no reprocessing.
