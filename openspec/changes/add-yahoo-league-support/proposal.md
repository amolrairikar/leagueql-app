## Why

LeagueQL supports ESPN and Sleeper today. Yahoo Fantasy is the remaining major
platform managers ask for, but it requires an OAuth 2.0 handshake (unlike ESPN's
cookies or Sleeper's public API), so it is a larger, roadmap-level effort that is
**not yet officially committed**.

The `backend/yahoo-oauth` and `frontend/connect-yahoo-league` capability specs were
authored ahead of implementation during the initial OpenSpec migration and lived in
`openspec/specs/` as if they described shipped behavior. No Yahoo code has ever been
committed (no routes, no frontend, no OpenAPI paths, no Terraform; the platform enum
is `['espn', 'sleeper']`), so those live specs were drift — asserting `SHALL` behavior
the system does not have.

This change originally reclassified that planned behavior as a pending proposal so
`openspec/specs/` described only implemented capabilities. Yahoo is now committed, so this
change **implements the account-linking increment**: the OAuth handshake, encrypted per-user
token persistence, transparent refresh, the onboarding gate, and the frontend Connect wiring.
The Yahoo Fantasy **data client** (actual league onboarding) is a follow-up increment; a
linked Yahoo onboard surfaces a neutral "coming soon" signal until then.

## What Changes

- Add the `Platform` enum value `YAHOO` (case-insensitive).
- Add `GET /leagues/yahoo/oauth/authorize` (Clerk-authed) and `GET /leagues/yahoo/oauth/callback` (public) to
  the API Lambda; declare both in `docs/api/openapi_spec.yaml` (callback omits `security:`).
- Store a single-use `state` (with pending `leagueId`) in a TTL'd DynamoDB item; store an
  encrypted per-user `YAHOO_OAUTH` token item (KMS); refresh transparently.
- Gate `POST /leagues` for Yahoo on a valid linked token; return the `YAHOO_AUTH` "link first"
  signal when unlinked and a neutral "coming soon" signal when linked.
- Frontend: offer Yahoo in the connect selector; Connect starts the OAuth redirect; the
  `/connect_league` return handles linked/declined and resumes onboarding.
- Infra: two API-GW routes, a KMS key, IAM for SSM/KMS/DynamoDB, and env vars for the SSM
  parameter names + redirect/return URLs.
- Docs: `openapi_spec.yaml`, `dynamodb_spec.md` (`YAHOO_OAUTH` + `OAUTH_STATE` items), and the
  architecture diagram (KMS + Yahoo integration).

## Capabilities

### New Capabilities
- `backend/yahoo-oauth`: OAuth 2.0 authorize/callback (client_secret, no PKCE), encrypted
  per-user token persistence, transparent refresh, and the "link Yahoo first" onboarding gate.
- `frontend/connect-yahoo-league`: Yahoo as a selectable Connect-League platform with the
  enter-league→Connect→OAuth round-trip, re-link/coming-soon states, and demo-mode handling.

## Impact

- **Specs:** re-seeds `openspec/specs/backend/yahoo-oauth/spec.md` and
  `openspec/specs/frontend/connect-yahoo-league/spec.md` on archive.
- **Code / infra / docs:** `src/api/` (routes, `yahoo_oauth.py`, `Platform` enum),
  `src/common/secrets.py`, KMS-encrypted `YAHOO_OAUTH` + `OAUTH_STATE` DynamoDB items,
  `frontend/src/features/{landing_page,connect_league}/`, `docs/api/openapi_spec.yaml`,
  `docs/db/dynamodb_spec.md`, `infrastructure/`, and the architecture diagram.
- **Non-goal:** the Yahoo Fantasy data client (onboarder integration) — a follow-up increment.
