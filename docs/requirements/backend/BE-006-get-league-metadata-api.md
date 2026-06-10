# BE-006: Get League Metadata API

## Description
Returns whether a league has been onboarded and, if so, its display name, the list of
onboarded seasons, and its subscription end time. `GET /leagues/{leagueId}` resolves the
platform league ID to a canonical league ID, reads the `METADATA` item, and lists seasons.
Used by the frontend to gate access (onboarded vs. not, subscription active vs. expired) and
to populate season selectors. This endpoint is **never** subscription-gated — the frontend
must be able to read `subscription_end_time` even when the subscription has lapsed
([BE-014](BE-014-subscription-access-control.md)).

## Scope
- Endpoint: `GET /leagues/{leagueId}?platform=` (`src/api/routes.py::get_league`).
- Returns: `{ seasons: string[], league_name, subscription_end_time }`.

## Edge Cases
- **League not onboarded:** lookup miss returns `404` with an onboarding hint.
- **`subscription_end_time` absent:** returned as null/omitted (older items, or no billing
  value written yet); the frontend treats absent as expired.
- **`league_name` absent:** may be null/omitted (older items); frontend must tolerate it.
- **Seasons ordering:** seasons returned sorted (ascending).
- **Migrated league:** seasons span all platforms under one canonical league ID.
- **Caching:** must respond `Cache-Control: no-store` (state can change after onboard/refresh).

## Acceptance Criteria
- [ ] `GET /leagues/{leagueId}` for an onboarded league returns `200` with `seasons`,
      `league_name`, and `subscription_end_time`.
- [ ] An un-onboarded league returns `404`.
- [ ] `subscription_end_time` is null/omitted when the attribute is absent.
- [ ] This endpoint is not subscription-gated (always reachable for onboarded leagues).
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
