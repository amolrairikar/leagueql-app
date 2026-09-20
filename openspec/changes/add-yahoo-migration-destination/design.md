## Context

See `proposal.md` — Why. Migration Step 2 fetches destination members two ways today: ESPN via the owner-gated backend proxy `POST /leagues/{leagueId}/espn_members` (`src/api/routes.py:362`), Sleeper via a direct public browser fetch. Yahoo has neither — it needs an OAuth-authenticated read. The Yahoo token is user-level (`PK=USER#{clerk_user_id}, SK=YAHOO_OAUTH`, KMS-encrypted); `src/api/yahoo_oauth.py` exposes `has_valid_link` / `get_valid_access_token` in the API Lambda. The onboarder's `src/onboarder/yahoo_client.py` already resolves a numeric league id → `league_key` (`_resolve_seasons`/`_parse_user_leagues`) and parses managers (`_filter_teams`), but that module is not importable from the API Lambda (it pulls the full onboarder client). Both Lambdas can import `src/common/` (that is how `common/yahoo_tokens.py` is shared).

## Goals / Non-Goals

**Goals:**
- Fetch a Yahoo destination league's managers for the mapping exercise, using the caller's linked token.
- Let an unlinked owner link Yahoo inline and resume the wizard automatically.
- Keep the members fetch/parse in one place shared by both Lambdas.

**Non-Goals:**
- The Yahoo destination *onboarding* leg (onboarder building a `YahooClient` on a MIGRATE run) — delivered by the in-flight `add-yahoo-data-client` change. This change only forwards `owner_user_id` and gates the request.
- A standalone "link Yahoo" settings entry point; linking stays flow-initiated (connect or migrate).
- Any change to ESPN/Sleeper destination behavior.

## Decisions

**1. Shared `src/common/yahoo_members.py` over duplicating parse logic.** The API Lambda cannot import `onboarder/yahoo_client.py`, but Yahoo's numeric-keyed/nested JSON normalization is subtle and already tested. Move the two pure helpers `_flatten`/`_collection_items` into `common/yahoo_members.py` as the single source of truth and have `yahoo_client.py` import them; add `resolve_league_key`, `parse_managers`, and `fetch_yahoo_members(access_token, numeric_league_id, *, http)` there. The heavier `_parse_user_leagues`/`_resolve_seasons` (season-lineage renew-chain) and `_filter_teams` (full team shape) stay in the onboarder — the proxy needs only id→key and managers. *Alternative:* self-contained copy in the API — rejected as duplicated fragile parsing.

**2. New owner-gated route `POST /leagues/{leagueId}/yahoo_members`** mirroring `get_espn_members`: `{leagueId}` is the numeric source league (owner-gated via `lookup_league` + `require_league_owner`); the destination Yahoo id is the `yahooLeagueId` query param (`^\d+$` → 422). Distinct statuses: 403 (no valid link / `YahooReauthRequired`), 404 (`YahooLeagueNotFound` — entered league not among the caller's Yahoo leagues), 502 (upstream HTTP/network/parse). Empty request body — the token is resolved server-side from the Clerk user.

**3. Return-context `flow` on the OAuth state** rather than a second authorize/callback pair. `create_oauth_state(..., flow="ONBOARD")` stores `flow`; `consume_oauth_state` returns it; the authorize route accepts `flow` (`ONBOARD`|`MIGRATE`, default `ONBOARD`); the callback chooses its redirect base — a new env-configured `YAHOO_MIGRATE_RETURN_URL` (default `.../migrate_league`) beside `YAHOO_CONNECT_RETURN_URL` — from the consumed state's `flow`. This keeps a single handshake and preserves existing connect behavior by default.

**4. Inline resume in the migrate page.** The source league context comes from cookies (`getLeagueCookies`) and survives the full-page redirect, so only the destination (Yahoo + entered id) must be reconstructed — carried back in the callback URL (`yahooLinked`, `leagueId`). A `useRef`-guarded effect (mirroring `startedRef` in `yahoo-connect-return.tsx:50`) detects the return, seeds `newPlatformInfo`, auto-calls `getYahooMembers`, and advances to Step 3; `yahooLinked=0` lands on Step 2 with a retry message.

**5. Forward `owner_user_id` from `migrate_league`.** `onboard_league` already passes `owner_user_id=clerk_user_id` (`routes.py:344`); `migrate_league` does not (`routes.py:525`). Migration is owner-gated, so the caller is the owner — safe for all destinations, required for Yahoo.

## Risks / Trade-offs

- **Owner must be a member of the destination Yahoo league** (Yahoo only exposes the authenticated user's leagues) → `resolve_league_key` returns `None` → 404 with a distinct message, so the UI can say "that Yahoo league isn't in your account" rather than a generic failure.
- **Link expires/revoked mid-flow** → `get_valid_access_token` raises `YahooReauthRequired`; the route maps it to 403 so the UI re-runs OAuth (same signal as never-linked).
- **Declined OAuth on the migrate flow** → the callback must consume the echoed `state` on the error path to recover `flow`; without it the user would bounce to `/connect_league`. Mitigation: consume-first when `state` is present, fall back to connect only when there is none.
- **StrictMode double-invoke** of the resume effect would double-fetch / mint two states → `useRef` guard.
- **Moving `_flatten`/`_collection_items`** touches the working onboarder client → covered by existing onboarder unit tests plus new `common` unit tests; the move is import-only, no behavior change.

## Migration Plan

Ships behind the existing dropdown (Yahoo was already listed). Deploy order: backend API (new route + `flow` + `YAHOO_MIGRATE_RETURN_URL` env) before/with the frontend so the OAuth return target exists. No data migration. Rollback: revert the route/handler/frontend; the `flow` state attribute is additive and backward-compatible (absent → `ONBOARD`).
