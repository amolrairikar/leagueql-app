# BE-007: Delete League API

## Description
Deletes an onboarded league and all of its associated data. `DELETE /leagues/{leagueId}`
resolves the canonical league ID, removes all DynamoDB items for the league, deletes the raw
API payloads from S3, and decrements the global `LEAGUE_COUNT`.

## Scope
- Endpoint: `DELETE /leagues/{leagueId}?platform=` (`src/api/routes.py::delete_league`).
- Helpers: `delete_all_league_items`, `update_league_count`.
- S3 prefix deleted: `raw-api-data/{canonical_league_id}/`.

## Edge Cases
- **League not onboarded:** lookup miss returns `404`.
- **No S3 objects present:** delete proceeds (S3 deletion is best-effort / no-op if empty).
- **>1000 S3 objects:** S3 `delete_objects` handles up to 1,000 keys per request;
  larger sets must be batched.
- **DynamoDB/S3 client error:** return `500` "Failed to delete league".
- **`LEAGUE_LOOKUP` entries across platforms (migrated league):** all lookup entries for
  the canonical league must be removed, not just the one queried.
- **Idempotency:** deleting an already-deleted league should not leave `LEAGUE_COUNT`
  inconsistent.

## Acceptance Criteria
- [ ] `DELETE /leagues/{leagueId}` for an onboarded league returns `200` "Successfully
      deleted league".
- [ ] All DynamoDB items (metadata, lookups, precomputed views) for the canonical league
      are removed.
- [ ] All raw API payloads under the league's S3 prefix are deleted.
- [ ] `LEAGUE_COUNT` is decremented by 1.
- [ ] Deleting an un-onboarded league returns `404`.
- [ ] Backend errors during deletion return `500`.

## Authorization (BE-016)
Delete is **owner-gated** ([BE-016](BE-016-league-ownership-authorization.md)): only the league owner can delete; a non-owner gets `403` before any data is touched.

## Sources
`src/api/routes.py::delete_league`, `src/api/helpers.py` (`delete_all_league_items`),
`docs/api/openapi_spec.yaml`.
