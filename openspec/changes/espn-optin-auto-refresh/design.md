## Context

See proposal.md — Why. Yahoo already stores OAuth tokens KMS-encrypted
(`src/common/yahoo_tokens.py`), the onboarder resolves them lazily by `owner_user_id`
(`src/onboarder/yahoo_client.py`), and the scheduler (`src/league_refresh/`) auto-refreshes Yahoo +
Sleeper. ESPN cookies (`SWID` + `espn_s2`) are currently supplied per-request and never stored, so
the scheduler hard-excludes ESPN (`REFRESH_PLATFORMS = (SLEEPER, YAHOO)`). `owner_user_id` is
already written to the `METADATA` item for every platform (`src/onboarder/writer.py`), and the
scheduler already resolves it from `METADATA` for Yahoo. The existing KMS key (`aws_kms_key.yahoo_tokens`,
alias `leagueql-yahoo-token-${env}`) is already granted `kms:Encrypt`/`Decrypt` to the API +
onboarder roles.

## Goals / Non-Goals

**Goals:**
- Persist ESPN cookies encrypted so the scheduler can refresh ESPN leagues on the owner's behalf.
- Make scheduled auto-refresh opt-in per league for both ESPN and Yahoo via one `auto_refresh_enabled`
  flag, reusing the existing owner-resolution path.
- Reuse Yahoo's encryption, storage lifecycle, and onboarder credential-resolution patterns rather
  than inventing new ones.

**Non-Goals:**
- Changing Sleeper (stays automatic, no credentials).
- Auto-renewing/refreshing ESPN cookies (ESPN has no refresh mechanism; expiry surfaces as `ESPN_AUTH`).
- Backfilling existing Yahoo leagues as enrolled (they require explicit re-opt-in — a deliberate
  behavior change, see proposal BREAKING note).
- Renaming the shared KMS key/env vars (optional follow-up; not required here).

## Decisions

- **Mirror Yahoo, don't generalize prematurely.** New `src/common/espn_credentials.py`
  (`EspnCredentialClient`) closely mirrors `YahooTokenClient`: same KMS `encrypt`/`decrypt`, a
  per-user item `USER#{clerk_user_id} / ESPN_CREDENTIALS` with encrypted `swid` + `espn_s2`, and a
  `from_env()`. No refresh/PKCE logic (ESPN has none). *Alternative considered:* one shared
  `CredentialClient` for both platforms — rejected to avoid churn on the working Yahoo path; a later
  refactor can unify if desired.
- **The onboarder owns encrypt + decrypt.** On a successful opted-in ESPN onboard/refresh the
  onboarder stores the cookies (so only cookies that actually authenticated are persisted); on a
  scheduled ESPN refresh (invoked with `owner_user_id` and no cookies) it fetches + decrypts them —
  exactly mirroring `yahoo_client.py` lazy token resolution. *Alternative:* the scheduler decrypts
  and passes plaintext cookies in the async invoke body — rejected: the code already avoids putting
  ESPN cookies in the invoke event, and this keeps KMS grants off the `league_refresh` role.
- **Single `auto_refresh_enabled` flag on `METADATA`** drives selection for both ESPN and Yahoo. The
  scheduler already reads `METADATA` per Yahoo league for the owner; extend that read to also project
  the flag and to cover ESPN. Absent = not enrolled, which naturally implements Yahoo's required
  re-opt-in. *Alternative:* a flag on `LEAGUE_LOOKUP` (already returned by the GSI2 scan) — rejected:
  the flag is per-canonical, and the scheduler already fetches `METADATA` for the owner anyway.
- **Shared KMS key.** `EspnCredentialClient` reads `ESPN_KMS_KEY_ID`/`ESPN_KMS_REGION`, but those env
  vars point at the *same* existing key/region as `YAHOO_KMS_*`, so no new key and no new IAM grant.
- **Opt-in surfaces.** ESPN opts in through the connect/refresh form checkbox (cookies + flag stored
  together via the onboarder). Yahoo opts in at link time and via a new owner-only
  `PUT /leagues/{leagueId}/auto-refresh` endpoint (tokens already stored, so the flag alone suffices);
  a sidebar toggle exposes the endpoint for existing leagues, routing ESPN "enable" to the connect
  form because fresh cookies are required.
- **Cleanup keyed on "no opted-in ESPN league remains."** On opt-out (the PUT endpoint) and on
  league delete, if the owner has no other ESPN league with `auto_refresh_enabled = true`, delete
  their `ESPN_CREDENTIALS` — a direct parallel to the existing Yahoo "delete tokens on last league"
  cleanup in `delete-league`, reusing the same owner-leagues query approach.

## Risks / Trade-offs

- **ESPN cookies expire and can't be refreshed** → scheduled refresh fails with `ESPN_AUTH` (already
  non-paging). The stale-data reminder banner already shows for a stale ESPN owner, so an
  opted-in-but-expired league naturally re-nudges the owner to re-enter cookies; the banner needs only
  a non-behavioral copy update (its premise that ESPN is manual-only is no longer the whole story).
- **Yahoo behavior regression (BREAKING):** existing Yahoo leagues stop auto-refreshing until
  re-enabled. → Documented in changelog/docs; the sidebar toggle makes re-opting-in one click, and no
  data is lost (manual/on-demand refresh still works).
- **Storing ESPN credentials widens the sensitive-data surface.** → Encrypted at rest under the same
  KMS key as Yahoo, never logged/traced/returned, stored only on explicit opt-in and only after a
  successful fetch, and deleted when no opted-in ESPN league remains.
- **Owner-leagues cleanup query is best-effort** (mirrors Yahoo) → its failure is logged/alerted and
  never fails the opt-out or delete.

## Migration Plan

1. Deploy backend + infra (env vars pointing at the shared key) — additive; no data migration. The
   `auto_refresh_enabled` flag is absent on existing leagues, so ESPN and Yahoo are simply not
   auto-refreshed until owners opt in (Yahoo's intended re-opt-in).
2. Deploy frontend (checkbox, sidebar toggle, docs/privacy/changelog).
3. Rollback: revert frontend and backend; stored `ESPN_CREDENTIALS` items become dormant (unused)
   and are removed on the next opt-out/delete, or can be manually purged. No schema migration to undo.
