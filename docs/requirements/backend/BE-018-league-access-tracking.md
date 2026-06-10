# BE-018: League Access Tracking

## Description
Records when a league was last opened so stale leagues — ones nobody has viewed in a long
time — can later be identified for pruning/archival. When a member opens a league via
`GET /leagues/{leagueId}` ([BE-006](BE-006-get-league-metadata-api.md)), the endpoint records a
`last_accessed_at` ISO-8601 (UTC) timestamp on the league's `METADATA` item. The write is
**throttled to at most once per hour per league**: `get_league` already reads the `METADATA`
item, so the throttle is evaluated in memory against the existing `last_accessed_at` and the
write is skipped when the value is still fresh — fresh accesses cost zero extra DynamoDB ops.

The field is **internal**: it is not returned in any API response and the OpenAPI contract is
unchanged. There is no consumer of `last_accessed_at` yet; the cleanup/archival job that reads
it is a separate, future change.

## Scope
- Write site: `src/api/routes.py::get_league` calls `helpers.record_league_access(...)` after the
  membership gate passes, reusing the already-fetched `metadata`.
- Helper: `src/api/helpers.py::record_league_access` (throttle check + conditional `update_item`).
- Throttle window: `LEAGUE_ACCESS_THROTTLE_SECONDS` in `src/api/main.py` (default 3600).
- Item: `METADATA` (`PK=LEAGUE#{canonical_league_id}`, `SK=METADATA`), attribute `last_accessed_at`.

## Edge Cases
- **`last_accessed_at` absent** (older items / never opened): treated as stale → the timestamp is
  written.
- **Fresh timestamp** (within the last hour): the write is **skipped** (no `update_item` call).
- **Stale timestamp** (older than an hour): a new timestamp is written.
- **Malformed/unparseable stored timestamp:** treated as stale → a fresh timestamp is written.
- **Concurrent league delete:** the write is conditional on `attribute_exists(PK)`; a
  conditional-check failure is expected and swallowed silently (no resurrection of a deleted item).
- **DynamoDB error on the write:** logged at warning and swallowed — the read still returns `200`.
  Recording access must never break the league read.
- **ESPN gating:** access is recorded only after `require_league_member` passes, so a `403`'d
  non-member never updates the timestamp. **Sleeper** has no membership concept, so any
  authenticated caller opening a Sleeper league records access.

## Acceptance Criteria
- [ ] Opening an onboarded league via `GET /leagues/{leagueId}` writes `last_accessed_at` on the
      `METADATA` item when the attribute is absent.
- [ ] A league whose `last_accessed_at` is within the last hour is **not** re-written on a
      subsequent open (throttle holds).
- [ ] A league whose `last_accessed_at` is older than an hour is re-written with a fresh value.
- [ ] A failure of the tracking write (DynamoDB error or conditional-check failure) does not
      change the endpoint response — `GET /leagues/{leagueId}` still returns `200`.
- [ ] `last_accessed_at` is never included in any API response and the OpenAPI spec is unchanged.

## Sources
`src/api/routes.py::get_league`, `src/api/helpers.py::record_league_access`,
`src/api/main.py` (`LEAGUE_ACCESS_THROTTLE_SECONDS`), `docs/db/dynamodb_spec.md` (METADATA).
