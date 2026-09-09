## 1. Spec-inventory correction (done earlier)

- [x] 1.1 Remove `openspec/specs/backend/yahoo-oauth/` and
  `openspec/specs/frontend/connect-yahoo-league/` from the live specs (they described
  unimplemented behavior).
- [x] 1.2 Preserve their requirements as delta specs under this change's
  `specs/backend/yahoo-oauth/` and `specs/frontend/connect-yahoo-league/`.
- [x] 1.3 Confirm no other spec cross-references the Yahoo capabilities, and
  `openspec validate --all` passes.

## 2. Spec updates for the linking increment (this step)

- [x] 2.1 Use PKCE (S256) + client_secret Basic auth in `backend/yahoo-oauth` (Yahoo requires
  PKCE — an earlier no-PKCE iteration was rejected by the live API).
- [x] 2.2 Change `frontend/connect-yahoo-league` to the enter-league→Connect→OAuth UX with a
  `/connect_league` return target.
- [x] 2.3 Scope this increment to OAuth linking only (no Yahoo data client); linked onboard
  returns a "coming soon" signal. Update `proposal.md` / `design.md`.

## 3. Backend — Yahoo OAuth

- [x] 3.1 Add `YAHOO` to the `Platform` enum (case-insensitive).
- [x] 3.2 `GET /leagues/yahoo/oauth/authorize` (Clerk-authed): mint a single-use `state` bound to the
  caller + pending `leagueId`, persist a TTL'd `OAUTH_STATE#{state}` item, return the
  `request_auth` consent URL (`client_id` from SSM, registered `redirect_uri`,
  `response_type=code`).
- [x] 3.3 `GET /leagues/yahoo/oauth/callback` (public): validate + consume `state`, exchange the code
  at `/get_token` with `Authorization: Basic base64(id:secret)`, persist a KMS-encrypted
  `YAHOO_OAUTH` item keyed by Clerk user, `302` to `/connect_league?platform=YAHOO&yahooLinked=1&leagueId=…`;
  `access_denied`/failure/invalid-state → `302` with `yahooLinked=0`, no partial write.
- [x] 3.4 Transparent refresh (`grant_type=refresh_token`) on expiry skew; `invalid_grant` →
  `YahooReauthRequired` (`YAHOO_AUTH` re-link signal). `client_id`/`client_secret` from
  SecureString SSM via `src/common/secrets.py`.
- [x] 3.5 Gate `POST /leagues` for Yahoo: unlinked → 403 "link first"; linked →
  `YAHOO_COMING_SOON` signal.
- [x] 3.6 Backend unit (`test_yahoo_oauth.py`, `test_yahoo_endpoints.py`, enum) + component
  (`yahoo_oauth.feature`) tests — authorize/callback/refresh, gating, token secrecy.

## 4. Frontend — Connect Yahoo league

- [x] 4.1 Add Yahoo to the landing-page platform selector.
- [x] 4.2 Connect with Yahoo → call `GET /leagues/yahoo/oauth/authorize?leagueId=…`, full-page redirect.
- [x] 4.3 `/connect_league` return (`YahooConnectReturn`): `yahooLinked=1` → connected state +
  resume onboard (renders the "coming soon" notice); `yahooLinked=0` → inline retry alert;
  403 → reconnect prompt; disabled in demo mode.
- [x] 4.4 jest-cucumber component tests (`yahoo-connect` + landing OAuth-start scenario).

## 5. Infra / docs

- [x] 5.1 Add the two API-GW routes to `docs/api/openapi_spec.yaml` (callback public).
- [x] 5.2 Terraform: single KMS key + IAM for SSM/KMS on the API role in **both** global
  stacks (dev + prod); API Lambda env vars (SSM param names, KMS key/region) plus
  `yahoo_redirect_uri`/`yahoo_connect_return_url` regional vars (prod defaults; dev overrides).
- [x] 5.3 Update `docs/db/dynamodb_spec.md` (`YAHOO_OAUTH` + `OAUTH_STATE` items) and the
  architecture diagram (KMS + Yahoo integration); regenerated the PNG.

## 6. Wrap-up

- [x] 6.1 `openspec validate` green; ruff/eslint/prettier/terraform-fmt clean; backend unit
  (804) + component (63) + frontend (278) tests pass.
- [ ] 6.2 Apply → archive once the data-client increment also lands (or archive the linking
  capability if the team prefers incremental archival).

## 7. Follow-ups (next increment)

- [ ] 7.1 Yahoo Fantasy **data client** in the onboarder (leagues/teams/matchups/draft/
  transactions + transforms), replacing the "coming soon" gate.
- [ ] 7.2 Revisit cross-region KMS for `get_valid_access_token` decryption (this increment
  pins one us-east-1 key; only encryption + existence checks run today).
