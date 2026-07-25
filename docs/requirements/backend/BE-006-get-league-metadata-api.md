# BE-006: Get League Metadata API

## Description
Returns whether a league has been onboarded and, if so, its display name and the list of
onboarded seasons. `GET /leagues/{leagueId}` resolves the platform league ID to a canonical
league ID, reads the `METADATA` item, and lists seasons. Used by the frontend to determine
whether a league is onboarded and to populate season selectors.

## Scope
- Endpoint: `GET /leagues/{leagueId}?platform=` (`src/api/routes.py::get_league`).
- Returns: `{ seasons: string[], league_name, is_owner }`.

## Edge Cases
- **League not onboarded:** lookup miss returns `404` with an onboarding hint.
- **`league_name` absent:** may be null/omitted (older items); frontend must tolerate it.
- **Seasons ordering:** seasons returned sorted (ascending).
- **Migrated league:** seasons span all platforms under one canonical league ID.
- **Caching:** must respond `Cache-Control: no-store` (state can change after onboard/refresh).

## Acceptance Criteria
- [ ] `GET /leagues/{leagueId}` for an onboarded league returns `200` with `seasons` and
      `league_name`.
- [ ] An un-onboarded league returns `404`.
- [ ] Response sets `Cache-Control: no-store`.
- [ ] `seasons` is the unified, sorted list across all platforms for migrated leagues.

## Authorization (BE-016)
The response includes `is_owner` so the frontend can gate owner-only actions. For **ESPN**
leagues this endpoint is **member-gated** ([BE-016](BE-016-league-ownership-authorization.md)) — a
non-member gets `403` before any metadata is returned; **Sleeper** reads stay open to any
authenticated caller.

## Access tracking (BE-018)
On a successful open (after the membership gate), `get_league` records a `last_accessed_at`
timestamp on the `METADATA` item, throttled to once per hour, so stale leagues can later be
identified ([BE-018](BE-018-league-access-tracking.md)). The write is best-effort and never
affects this endpoint's response.

## Sources
`src/api/routes.py::get_league`, `docs/db/dynamodb_spec.md` (METADATA).
