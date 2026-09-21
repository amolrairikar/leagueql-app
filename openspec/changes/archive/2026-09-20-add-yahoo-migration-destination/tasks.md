## 1. Shared Yahoo members module

- [x] 1.1 Create `src/common/yahoo_members.py` with the pure helpers `_flatten` and `_collection_items` (moved from `src/onboarder/yahoo_client.py`), `resolve_league_key(user_leagues_payload, numeric_league_id) -> str | None`, `parse_managers(teams_payload) -> list[dict]` (`{owner_id: guid or manager_id, display_name: nickname or owner_id}`), a `YahooLeagueNotFound` exception, and `fetch_yahoo_members(access_token, numeric_league_id, *, http)` (GET `/users;use_login=1/games;game_codes=nfl/leagues?format=json` → resolve key → GET `/league/{key}/teams?format=json` → parse); verify with new unit tests in 4.1
- [x] 1.2 Update `src/onboarder/yahoo_client.py` to import `_flatten`/`_collection_items` from `common.yahoo_members` and drop its local copies; verify `pipenv run pytest tests/unit/onboarder` (yahoo client tests) still pass

## 2. Backend API

- [x] 2.1 Add `POST /leagues/{leagueId}/yahoo_members` in `src/api/routes.py` (owner-gated like `get_espn_members`): `yahooLeagueId` query param `^\d+$`; resolve the token via `yahoo_oauth.get_valid_access_token`; call `fetch_yahoo_members`; map no-link/`YahooReauthRequired`→403, `YahooLeagueNotFound`→404, upstream error→502; return `APIResponse(data=[{owner_id, display_name}])`; verify with unit tests in 4.2
- [x] 2.2 Add a `flow` return-context to `src/api/yahoo_oauth.py`: `create_oauth_state(clerk_user_id, league_id, flow="ONBOARD")` persists `flow`; `consume_oauth_state` returns `item.get("flow", "ONBOARD")`; verify with unit tests in 4.3
- [x] 2.3 In `src/api/routes.py`, accept an optional `flow` (`ONBOARD`|`MIGRATE`, default `ONBOARD`) on `yahoo_authorize` and forward it; in `yahoo_callback` consume `state` (including on the declined/`error` path when present) and pick the redirect base by `flow` — `/migrate_league` for `MIGRATE`, `/connect_league` otherwise; verify with unit tests in 4.3
- [x] 2.4 Add `YAHOO_MIGRATE_RETURN_URL` (env-configured, default `.../migrate_league`) in `src/api/main.py` beside `YAHOO_CONNECT_RETURN_URL`; verify it is read in `yahoo_callback`
- [x] 2.5 In `migrate_league` (`src/api/routes.py`), gate a Yahoo destination on `yahoo_oauth.has_valid_link` (403 "Link your Yahoo account first") and pass `owner_user_id=clerk_user_id` to `invoke_onboarder`; verify with unit tests in 4.2
- [x] 2.6 Update `docs/api/openapi_spec.yaml` with the `yahoo_members` route and the authorize `flow` param; verify the file lints/parses

## 3. Frontend

- [x] 3.1 In `frontend/src/features/migrate_league/api-calls.ts` add `YahooMemberEntry { owner_id, display_name }` and `getYahooMembers(leagueId, platform, yahooLeagueId)` → `POST /leagues/${leagueId}/yahoo_members?{platform,yahooLeagueId}` (empty body); verify via the frontend tests in 4.4
- [x] 3.2 Extend `getYahooAuthorizeUrl(leagueId, flow?)` in `frontend/src/features/connect_league/api-calls.ts` to append `flow` when provided; verify via the frontend tests in 4.4
- [x] 3.3 In `frontend/src/features/migrate_league/migrate-league.tsx`: extend `NewPlatformUser` with `YahooMemberEntry`; add a Yahoo Step-2 branch (league-id only, no season/cookies) that calls `getYahooMembers`, and on `ApiError 403` swaps the Next button for a "Connect with Yahoo" button calling `getYahooAuthorizeUrl(yahooLeagueId, 'MIGRATE')` then `window.location.href`; verify via the frontend tests in 4.4
- [x] 3.4 Add a `useRef`-guarded return-resume effect on the `MigrateLeague` component: on `platform=YAHOO&yahooLinked=1&leagueId=<id>` seed the Yahoo destination, auto-fetch members, advance to Step 3; on `yahooLinked=0` land on Step 2 with a cancelled/retry message; verify via the frontend tests in 4.4

## 4. Tests

- [x] 4.1 New `tests/unit/common/test_yahoo_members.py`: `_flatten`/`_collection_items`, `resolve_league_key` hit/miss, `parse_managers` (guid vs manager_id, nickname fallback), `fetch_yahoo_members` happy path + `YahooLeagueNotFound`; verify `pipenv run pytest tests/unit/common/test_yahoo_members.py`
- [x] 4.2 Extend `tests/unit/api/test_endpoints.py`: `yahoo_members` happy path / 403 no-link / 403 non-owner / 404 not-in-account / 502 upstream / 422 bad id; migrate Yahoo-no-link→403 and `invoke_onboarder` called with `owner_user_id`; verify `pipenv run pytest tests/unit/api/test_endpoints.py`
- [x] 4.3 Extend `tests/unit/api/test_yahoo_oauth.py`: `flow` persisted/returned; authorize forwards it; callback routes to the migrate base for `MIGRATE` and the connect base otherwise (incl. declined path recovering `flow`); verify `pipenv run pytest tests/unit/api/test_yahoo_oauth.py`
- [x] 4.4 Frontend jest-cucumber additions in `frontend/src/features/migrate_league/__tests__/` (MSW handlers for `/leagues/:id/yahoo_members` and `/leagues/yahoo/oauth/authorize`): linked happy path→map→submit→home; not-linked→403→"Connect with Yahoo"→click sets `window.location.href`; OAuth return `?platform=YAHOO&yahooLinked=1&leagueId=999` with cookies→auto-fetch→Step 3 visible; verify `npx vitest run src/features/migrate_league`
- [x] 4.5 New Behave `tests/component/features/yahoo_members_proxy.feature` (mirror `espn_members_proxy.feature`) + steps in `tests/component/steps/api_steps.py`, and a Yahoo-destination scenario in `features/league_migration.feature`; verify `pipenv run behave tests/component`

## 5. Validate

- [x] 5.1 `pipenv run ruff check --fix . && pipenv run ruff format .`; from `frontend/`: `npm run lint` and `npm run format:check`
- [x] 5.2 `openspec validate --all` passes; then run the OpenSpec archive workflow when implementation is complete
