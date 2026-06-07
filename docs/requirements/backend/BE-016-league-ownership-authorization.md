# BE-016: League Ownership & Authorization

## Description
Binds each league to an **owner** and gates state-changing endpoints to that owner, and gates
**reads of ESPN leagues** to verified **members**. This closes the LQL-01 Broken Object-Level
Authorization finding: previously every league route accepted any valid Clerk JWT and acted on
the league ID in the path, so any authenticated user could delete, migrate, refresh, or read any
league.

- **Owner.** The Clerk user who first onboards a league is its owner
  (`owner_user_id` on the `METADATA` item, set once on first ONBOARD; REFRESH/MIGRATE never
  overwrite it). `require_league_owner` compares the caller to the owner and raises `403`
  otherwise. Owner-gated endpoints: delete, migrate, refresh, ESPN-members proxy, checkout
  session, and mint-transfer-token.
- **ESPN read membership.** ESPN league data is confidential (viewing it upstream requires the
  caller's `espn_s2`/`SWID` cookies), so `GET /leagues/{id}` and `GET /leagues/{id}/query` are
  member-gated for ESPN via `require_league_member` (`403` for non-members). Membership is the
  `members` string set on `METADATA`, seeded with the owner at onboard. **Sleeper reads stay
  open** (Sleeper's API is public) — the gate is a no-op for Sleeper.
- **Membership verification.** A non-member joins through `POST /leagues/{id}/verify-membership`:
  the Chrome extension fills the caller's ESPN cookies, the backend proxies an authenticated read
  of that exact ESPN league with those cookies, and a success adds the caller's Clerk user ID to
  `members`. Cookies ESPN rejects leave the caller unauthorized (`403`).
- **Ownership transfer.** `POST /leagues/{id}/transfer-token` (owner) mints a one-time token
  (only its sha256 hash + a 24h expiry are stored); `POST /leagues/{id}/claim-ownership`
  (authenticated) redeems it, swapping `owner_user_id` and adding the new owner to
  `members` via a single-use, race-safe conditional write. Abandoned-owner recovery is manual
  (support), not automated.
- **`is_owner`.** `GET /leagues/{id}` returns `is_owner` so the frontend can gate owner-only
  affordances ([FE-025](../frontend/FE-025-ownership-transfer-owner-gated-actions.md)).

## Scope
- Helpers (`src/api/helpers.py`): `require_league_owner`, `require_league_member`,
  `add_league_member`.
- Owner capture threaded from the API through the async onboarder
  (`src/common/onboarder_invoke.py` → `src/onboarder/handler.py` →
  `onboarding_service.py` → `writer.py::write_league_records`, ONBOARD branch only).
- Owner-gated routes and member-gated reads (`src/api/routes.py`).
- New routes: `transfer-token`, `claim-ownership`, `verify-membership`.
- `METADATA` additions: `owner_user_id` (S), `members` (SS), `transfer_token_hash` (S),
  `transfer_token_expires_at` (S) — see [`dynamodb_spec.md`](../../db/dynamodb_spec.md).

## Edge Cases
- **No owner recorded** (system-initiated onboard, e.g. Sleeper auto-refresh): owner-gated
  endpoints raise `403`; recovery is manual.
- **Gate ordering:** owner gate runs before the subscription gate on migrate/ESPN-members and
  before trial logic on checkout; refresh runs the subscription gate first, then the owner gate.
- **Existence not hidden for Sleeper:** a non-member's `GET` of a Sleeper league still returns
  `200`; for ESPN the member gate also hides metadata (`403` before `league_name`/seasons).
- **Public ESPN league:** ESPN returns `2xx` even for cookies not in the league, so any
  authenticated caller could self-add — accepted, because a public ESPN league exposes the same
  data upstream anyway; the gate protects *private* leagues.
- **verify-membership on Sleeper:** rejected with `400` (verification only applies to ESPN).
- **verify-membership season:** derived from the league's onboarded seasons (latest), never
  taken from client input, keeping the upstream ESPN URL free of attacker-controlled characters.
- **claim-ownership errors:** `404` (no outstanding token / league), `403` (token mismatch),
  `410` (expired or unparseable expiry), `409` (token already redeemed — conditional write lost).
- **Single-use token:** redeeming removes the hash + expiry; a re-mint overwrites any prior token.

## Acceptance Criteria
- [ ] First ONBOARD records `owner_user_id` and seeds `members` with the owner; REFRESH and
      MIGRATE leave both untouched.
- [ ] `delete`, `migrate`, `refresh`, `espn_members`, `checkout`, and `transfer-token` return
      `403` for a non-owner and succeed for the owner.
- [ ] `GET /leagues/{id}` returns `is_owner` (true for the owner, false otherwise).
- [ ] ESPN `GET /leagues/{id}` and `GET /leagues/{id}/query` return `403` for a non-member and
      `200` for the owner/members; Sleeper reads stay open to any authenticated caller.
- [ ] `verify-membership` adds the caller to `members` on ESPN success (idempotent), returns
      `403` when ESPN rejects the cookies, `400` for non-ESPN, and `502` on ESPN/network error.
- [ ] `transfer-token` (owner) returns a one-time plaintext token and stores only its hash +
      expiry; `claim-ownership` swaps the owner on a valid token and yields `404`/`403`/`410`/`409`
      for the no-token/mismatch/expired/already-redeemed cases.
- [ ] After a handoff, the new owner can mutate the league and the previous owner gets `403`.
- [ ] `create_billing_portal_session` (per-user) is unchanged; `get_job` is unchanged.

## Sources
`src/api/helpers.py` (`require_league_owner`, `require_league_member`, `add_league_member`),
`src/api/routes.py`, `src/common/onboarder_invoke.py`, `src/onboarder/{handler,onboarding_service,writer}.py`,
`docs/db/dynamodb_spec.md` (METADATA), `docs/api/openapi_spec.yaml`.
