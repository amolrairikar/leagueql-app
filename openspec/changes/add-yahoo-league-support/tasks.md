## 1. Spec-inventory correction (this change)

- [x] 1.1 Remove `openspec/specs/backend/yahoo-oauth/` and
  `openspec/specs/frontend/connect-yahoo-league/` from the live specs (they described
  unimplemented behavior).
- [x] 1.2 Preserve their requirements verbatim as delta specs under this change's
  `specs/backend/yahoo-oauth/` and `specs/frontend/connect-yahoo-league/`
  (`## ADDED Requirements`).
- [x] 1.3 Confirm no other spec cross-references the Yahoo capabilities, and
  `openspec validate --all` passes.

## 2. Backend — Yahoo OAuth (deferred until Yahoo is committed)

- [ ] 2.1 Add `GET /auth/yahoo/authorize` (Clerk-authed): build the consent URL with
  PKCE `code_challenge` (S256), `scope=fspt-r`, and a single-use `state` bound to the caller.
- [ ] 2.2 Add `GET /auth/yahoo/callback`: validate `state`, exchange the code via
  `oauth2/get_token` with the stored PKCE verifier + Basic auth, persist a KMS-encrypted
  `YAHOO_OAUTH` item, and `302` to a fixed frontend path with a linked/declined/failed marker.
- [ ] 2.3 Add transparent refresh (`grant_type=refresh_token`) on expiry skew and a
  `YAHOO_AUTH` re-link code on `invalid_grant`.
- [ ] 2.4 Read `client_id`/`client_secret` from SecureString SSM via `src/common/secrets.py`;
  keep them out of env vars, Terraform state, and CI.
- [ ] 2.5 Accept `YAHOO` case-insensitively in the `Platform` enum and gate `POST /leagues`
  for Yahoo on a valid linked token ("link Yahoo first" signal).
- [ ] 2.6 Backend unit + component tests (authorize/callback/refresh, member-gating,
  token secrecy); update `docs/api/openapi_spec.yaml` and `docs/db/dynamodb_spec.md`.

## 3. Frontend — Connect Yahoo league (deferred until Yahoo is committed)

- [ ] 3.1 Add Yahoo to the platform selector; show a "Connect your Yahoo account" CTA and
  disable submit while unlinked.
- [ ] 3.2 Wire the CTA to `GET /auth/yahoo/authorize` (full-page redirect) and handle the
  `platform=YAHOO&yahooLinked=1` return (linked state, league selection, strip marker params;
  inline retry alert on declined/failed).
- [ ] 3.3 League selection (dropdown + manual league-key fallback + empty state), onboard via
  `POST /leagues`, and poll `GET /jobs/{jobId}`.
- [ ] 3.4 `YAHOO_AUTH` reconnect prompt; keep tokens out of the browser; disable in demo mode.
- [ ] 3.5 jest-cucumber component tests for the two-step flow.

## 4. Cross-cutting

- [ ] 4.1 Update the architecture diagram if Yahoo adds a deployed component (e.g. a Yahoo
  client/worker or KMS key) and regenerate the PNG.
- [ ] 4.2 Apply → archive this change so both capabilities merge back into `openspec/specs/`.
