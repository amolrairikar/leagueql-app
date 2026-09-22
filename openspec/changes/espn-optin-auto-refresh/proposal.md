## Why

ESPN is the only platform LeagueQL never auto-refreshes: it needs the user's `SWID` + `espn_s2`
cookies, which are supplied per request and never stored, so the scheduled refresh Lambda
excludes ESPN and its owners must manually re-submit cookies every week. Yahoo already proves the
alternative — OAuth tokens are stored encrypted at rest and the scheduler refreshes on the
owner's behalf. We extend that pattern to ESPN by persisting its cookies encrypted, and, because
storing credentials is privacy-sensitive, we make auto-refresh **opt-in** for both credentialed
platforms.

## What Changes

- Persist a user's ESPN `SWID` + `espn_s2` cookies **encrypted at rest** (reusing the existing
  KMS key that already protects Yahoo tokens) in a per-user `ESPN_CREDENTIALS` item, so the
  scheduler can refresh ESPN leagues without the user re-entering cookies.
- Introduce a per-league `auto_refresh_enabled` flag (on the league `METADATA` item) that gates
  scheduled auto-refresh for **both ESPN and Yahoo**. Sleeper is unchanged (public, no
  credentials, stays automatic).
- **BREAKING (Yahoo behavior):** Yahoo becomes strictly opt-in. Existing Yahoo leagues stop being
  auto-refreshed until their owner re-enables it (no grandfather backfill).
- The scheduled refresh Lambda now selects ESPN and Yahoo leagues only when their flag is set,
  resolving the owner from `METADATA`; the onboarder fetches/decrypts the owner's stored ESPN
  cookies during a scheduled ESPN refresh. Expired ESPN cookies surface as the existing
  non-paging `ESPN_AUTH` failure.
- Stored ESPN cookies are deleted as soon as the user has no opted-in ESPN leagues left (on
  opt-out or league deletion), mirroring the Yahoo "delete tokens when last league removed" rule.
- New owner-only endpoint `PUT /leagues/{leagueId}/auto-refresh` to enable/disable the flag; the
  onboarder also sets the flag from an `autoRefresh` field on onboard/refresh.
- Frontend: an opt-in checkbox with an explanatory tooltip on the ESPN connect/refresh form and
  the Yahoo link flow, updated stale-data reminder copy, and updated privacy-policy, docs, and
  changelog content.

## Capabilities

### New Capabilities
- `backend/espn-credential-storage`: KMS-encrypted storage of a user's ESPN `SWID`/`espn_s2`
  cookies (`USER#{id} / ESPN_CREDENTIALS`) — encrypt/decrypt, store on opt-in, fetch by
  `owner_user_id`, and delete when no opted-in ESPN league remains. Mirrors `backend/yahoo-oauth`.

### Modified Capabilities
- `backend/scheduled-league-auto-refresh`: auto-refresh ESPN and Yahoo only when
  `auto_refresh_enabled` is set; drop the "ESPN excluded" exclusion; ESPN dispatch carries the
  owner id and the onboarder fetches the owner's stored cookies; opt-in preference is managed via
  a new endpoint and set at onboard/refresh.
- `backend/league-onboarding`: the onboarder persists `auto_refresh_enabled` on `METADATA` and
  stores/updates the owner's encrypted ESPN cookies when an ESPN onboard/refresh opts in.
- `backend/delete-league`: also delete the user's `ESPN_CREDENTIALS` item when their last
  opted-in ESPN league is removed.
- `frontend/connect-league`: ESPN form gains an "enable automatic weekly refresh" checkbox with an
  explanatory tooltip, prefilled from the league's current enrollment on refresh.
- `frontend/connect-yahoo-league`: the Yahoo link flow gains the same opt-in checkbox.
- `frontend/privacy-pages`: disclose that ESPN cookies are stored encrypted at rest **only when
  the user enables auto-refresh**, used solely to refresh league data, never shared, and removed
  when auto-refresh is turned off / the last ESPN league is removed.
- `frontend/instructions-docs`: document ESPN and Yahoo opt-in auto-refresh under "Refreshing
  League Data".

## Impact

- **Backend:** new `src/common/espn_credentials.py`; `src/onboarder/` (handler, onboarding
  service, writer); `src/league_refresh/utils.py`; `src/api/routes.py` + `src/api/main.py`
  (new endpoint, `autoRefresh` payload field, delete-league cleanup).
- **API contract:** new `PUT /leagues/{leagueId}/auto-refresh`; `autoRefresh` field on the
  onboard/refresh payload — update `docs/api/openapi_spec.yaml`.
- **Data model:** new `USER#{id} / ESPN_CREDENTIALS` item; new `auto_refresh_enabled` attribute
  on `LEAGUE#{canonical} / METADATA` — update `docs/db/dynamodb_spec.md`.
- **Infra:** add `ESPN_KMS_KEY_ID`/`ESPN_KMS_REGION` env vars (pointing at the existing shared KMS
  key) to the API + onboarder Lambdas in `infrastructure/regional/main.tf`; no new key or IAM
  grant. Update `docs/architecture/` if the credential store warrants a node.
- **Frontend:** `features/connect_league/*`, `features/sidebar/*`, `features/privacy/*`,
  `features/instructions/*`, `features/changelog/constants.ts`.
- **Tests:** backend unit + component (moto), frontend component (vitest + jest-cucumber).
