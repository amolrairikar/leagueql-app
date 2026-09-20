## Why

The league-migration wizard offers Yahoo as a destination platform but has no way to fetch a Yahoo league's members, so selecting it wrongly falls through to the ESPN branch and fails. Yahoo needs OAuth (no cookies, not public), so completing the manager-mapping exercise for a Yahoo destination requires an authenticated members fetch and a way to link Yahoo mid-wizard.

## What Changes

- **New backend proxy** `POST /leagues/{leagueId}/yahoo_members` (owner-gated): uses the caller's user-level Yahoo OAuth token to resolve the entered destination Yahoo numeric league id to a `league_key` and fetch that league's managers, returning `data: [{ owner_id, display_name }]`. Returns `403` when there is no valid link (re-link signal), `404` when the league isn't among the caller's Yahoo leagues, `502` on upstream failure, `422` on a non-numeric id.
- **Yahoo OAuth return-context**: the authorize/callback flow carries a `flow` marker (`ONBOARD` default, `MIGRATE`) so a migration-initiated link redirects the browser back into `/migrate_league` (prefilled `platform=YAHOO&yahooLinked=1|0&leagueId=<yahoo id>`) instead of `/connect_league`.
- **Migrate handler**: a Yahoo destination is gated on a valid Yahoo link (`403` "link Yahoo first"), and the migrate flow forwards `owner_user_id` to the onboarder so the destination onboard can resolve the owner's Yahoo token.
- **Frontend migration wizard**: a Yahoo Step-2 branch (league-id only — no season/cookies); an inline OAuth resume (a "Connect with Yahoo" button appears on the `403` not-linked signal, and a return-resume effect auto-fetches members and advances to the mapping step on the OAuth return).
- **Shared code**: a new `src/common/yahoo_members.py` holds the members fetch/parse, with the pure `_flatten`/`_collection_items` helpers moved there from `src/onboarder/yahoo_client.py` as the single source of truth.

## Capabilities

### New Capabilities
- `backend/yahoo-members-proxy`: server-side proxy that returns a Yahoo league's managers for the migration mapping, using the caller's linked Yahoo OAuth token (mirrors `backend/espn-members-proxy`).

### Modified Capabilities
- `backend/yahoo-oauth`: the authorize endpoint accepts a return-context `flow`, the single-use `state` carries it, and the callback routes to `/migrate_league` for `flow=MIGRATE` (and `/connect_league` otherwise).
- `backend/league-migration`: a Yahoo destination requires a linked Yahoo token (`403`, no `season`/cookies), and the migrate flow forwards `owner_user_id` to the onboarder.
- `frontend/migrate-league`: Yahoo destination members are fetched via the Yahoo proxy; an unlinked caller sees a "Connect with Yahoo" OAuth prompt; the OAuth return resumes the wizard.

## Impact

- **APIs**: new `POST /leagues/{leagueId}/yahoo_members`; `GET /leagues/yahoo/oauth/authorize` gains an optional `flow` param; `GET /leagues/yahoo/oauth/callback` redirect target becomes flow-dependent.
- **Backend code**: `src/api/routes.py` (new route, migrate gate + `owner_user_id`, authorize/callback), `src/api/yahoo_oauth.py` (`create_oauth_state`/`consume_oauth_state` carry `flow`), `src/api/main.py` (new `YAHOO_MIGRATE_RETURN_URL`), new `src/common/yahoo_members.py`, `src/onboarder/yahoo_client.py` (import moved helpers).
- **Frontend code**: `frontend/src/features/migrate_league/{migrate-league.tsx,api-calls.ts}`, `frontend/src/features/connect_league/api-calls.ts`.
- **Config/infra**: a `YAHOO_MIGRATE_RETURN_URL` value for the API Lambda.
- **Dependency**: end-to-end Yahoo-destination onboarding relies on the in-flight `add-yahoo-data-client` change (the onboarder building a `YahooClient` on a MIGRATE run); this change adds only the migration-destination wiring on top.
- **Docs**: keep `docs/api/openapi_spec.yaml` in sync with the new route and the `flow` param.
