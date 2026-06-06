# BE-009: ESPN Members Proxy API

## Description
Server-side proxy to the ESPN Fantasy API that returns the list of members (owners) for a
given ESPN league. `POST /leagues/{leagueId}/espn_members` makes the request from the Lambda
using the caller's `swid`/`s2` cookies, avoiding browser CORS restrictions. Primarily used
by the migration flow ([BE-003](BE-003-league-migration.md), [FE-003](../frontend/FE-003-migrate-league.md))
to build the manager identity mapping between platforms.

## Scope
- Endpoint: `POST /leagues/{leagueId}/espn_members?platform=&espnLeagueId=&season=`
  (`src/api/routes.py::get_espn_members`).
- Request body: `EspnMembersRequest` (`swid`, `s2`).
- Upstream: `https://lm-api-reads.fantasy.espn.com/.../leagues/{espnLeagueId}?view=mTeam`.

## Edge Cases
- **Input validation:** `espnLeagueId` and `season` are interpolated into the upstream ESPN
  URL, so both are constrained to digits only (`espnLeagueId` `^\d+$`, `season` `^\d{4}$`); a
  non-matching value returns `422` before any upstream request. This keeps attacker-controlled
  characters (`?`, `&`, `/`, `..`) out of the request path/query, preventing parameter
  injection / path traversal against the fixed ESPN host.
- **Current league not onboarded:** `lookup_league` miss returns `404`.
- **ESPN HTTP error (bad credentials / not found):** return `502` "Failed to fetch ESPN
  league members".
- **ESPN unreachable / network error:** return `502` "Failed to reach ESPN API".
- **Unparseable ESPN response:** return `502` "Failed to parse ESPN API response".
- **Member without `displayName`:** fall back to the member `id` as the display name.
- **Credentials handling:** `swid`/`s2` are used only for the proxied request; never logged
  or persisted.
- **Request timeout:** the upstream call uses a bounded timeout (10s).

## Acceptance Criteria
- [ ] `POST /leagues/{leagueId}/espn_members` returns `200` with
      `data: [{ owner_id, display_name }]` for a valid ESPN league + credentials.
- [ ] Members missing a display name fall back to their owner ID.
- [ ] Upstream HTTP/network/parse failures return `502` with the appropriate message.
- [ ] A non-onboarded current league returns `404`.
- [ ] A non-numeric `espnLeagueId` or a `season` that is not a 4-digit year returns `422`
      without making an upstream ESPN request.
- [ ] `swid`/`s2` never appear in logs or stored items.

## Sources
`src/api/routes.py::get_espn_members`, `docs/api/openapi_spec.yaml`.
