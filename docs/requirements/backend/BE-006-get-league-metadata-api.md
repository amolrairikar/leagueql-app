# BE-006: Get League Metadata API

## Description
Returns whether a league has been onboarded and, if so, its display name, the list of
onboarded seasons, and its subscription status. `GET /leagues/{leagueId}` resolves the
platform league ID to a canonical league ID, reads the `METADATA` item, and lists seasons.
Used by the frontend to gate access (onboarded vs. not) and to populate season selectors.

## Scope
- Endpoint: `GET /leagues/{leagueId}?platform=` (`src/api/routes.py::get_league`).
- Returns: `{ seasons: string[], league_name, subscription_status }`.

## Edge Cases
- **League not onboarded:** lookup miss returns `404` with an onboarding hint.
- **Subscription status absent:** reads default to `DEFAULT_SUBSCRIPTION_STATUS` (`ACTIVE`).
- **`league_name` absent:** may be null/omitted (older items); frontend must tolerate it.
- **Seasons ordering:** seasons returned sorted (ascending).
- **Migrated league:** seasons span all platforms under one canonical league ID.
- **Caching:** must respond `Cache-Control: no-store` (state can change after onboard/refresh).

## Acceptance Criteria
- [ ] `GET /leagues/{leagueId}` for an onboarded league returns `200` with `seasons`,
      `league_name`, and `subscription_status`.
- [ ] An un-onboarded league returns `404`.
- [ ] `subscription_status` defaults to `ACTIVE` when the attribute is absent.
- [ ] Response sets `Cache-Control: no-store`.
- [ ] `seasons` is the unified, sorted list across all platforms for migrated leagues.

## Sources
`src/api/routes.py::get_league`, `src/api/main.py` (`DEFAULT_SUBSCRIPTION_STATUS`),
`docs/db/dynamodb_spec.md` (METADATA).
