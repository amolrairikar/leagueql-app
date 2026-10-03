# Design

## Context

See proposal.md, Why. Membership is stored only on `LEAGUE#{id}` / `METADATA` as
`owner_user_id` (S) and `members` (SS). DynamoDB can't use a set as a GSI key. The only
"leagues for user X" path today is `_iter_owner_other_league_metadata`
(`src/api/helpers.py`). It queries GSI3 (every METADATA item) with a FilterExpression, so each
call costs O(all leagues), and GSI3 doesn't project `members`. Sleeper reads are open, so Sleeper
viewers aren't recorded at all.

Constraints:
- The API Lambda role allows `PutItem`, `GetItem`, `BatchGetItem`, `Query`, `UpdateItem`, and
  `DeleteItem`, but not `TransactWriteItems`. The onboarder already writes METADATA in a transaction.
- API Gateway routes are generated from `docs/api/openapi_spec.yaml` (`templatefile` in
  `infrastructure/modules/api-gw`). A new path needs its own OpenAPI entry with `security: ClerkJWT`
  and the Lambda `x-amazon-apigateway-integration`, or it won't be routed or authenticated.
- The UI is settled in the mockup (https://claude.ai/artifact/BMTQ45hJ9k13AxPXEAyLsV): list
  layout with no badges or filters.

## Goals / Non-Goals

**Goals:**
- Listing costs O(the user's leagues), not O(all leagues).
- The index is cleaned up automatically on league delete, and survives refresh and migration.
- Authorization behavior doesn't change.

**Non-Goals:**
- Letting a user remove a league from their list, or leave a league.
- Recovering Sleeper leagues opened before this ships.
- Using the index for authorization decisions.

## Decisions

### 1. Membership items in the league partition + sparse GSI4
Item: `PK=LEAGUE#{canonical_league_id}`, `SK=MEMBER#{clerk_user_id}`,
`member_user_id={clerk_user_id}`, `joined_at=<ISO 8601>`. **GSI4** has HASH `member_user_id`,
RANGE `joined_at`, and projection `KEYS_ONLY`. GSI4 is sparse because only these items carry
`member_user_id`.

- *Why the league partition:* `delete_all_league_items` already deletes every item under
  `LEAGUE#{id}`, so delete-league needs no new code, and a migration keeps the canonical ID.
- *Alternative: `PK=USER#{uid}`, `SK=LEAGUE#{id}`.* This needs no new GSI, but delete would
  have to fan out to each member's partition (owner plus `members`), and any mistake there leaves
  ghost leagues. Rejected.
- *Alternative: filter GSI3 by `contains(members, uid)`.* This is still O(all leagues), and it
  needs a GSI3 projection rebuild. Rejected.
- *No `role` attribute:* roles aren't displayed, and ownership stays authoritative on METADATA.
  That keeps ownership transfer to a single additive put.

### 2. Idempotent conditional puts, no API transactions
Every write is `PutItem` with `ConditionExpression=attribute_not_exists(PK)`. A
`ConditionalCheckFailedException` means "already indexed" and is swallowed, so `joined_at` stays
stable.

- **Onboard:** add the put to the existing `transact_items` in `src/onboarder/writer.py`, in the
  first-onboard branch, only when `owner_user_id` is set. It's atomic with METADATA. This one
  Put is **unconditional**, matching the unconditional METADATA Put beside it, so an async Lambda
  retry of the same onboard (same canonical ID) doesn't cancel the transaction on an
  already-written row.
- **Accept invite** (`add_league_member`) and **claim ownership:** do the put after the METADATA
  update succeeds. Partial failure: METADATA updated but the row missing means the user is
  authorized but not listed. Re-redeeming the invite or the backfill fixes it. A row failure
  returns `500` like the existing METADATA failure path, so the user can retry, and retrying is
  idempotent.
- **Sleeper open** (`get_league`): after `require_league_member`, when the effective platform
  (`active_platform or platform`) is `SLEEPER`, do a best-effort put. Every non-conditional error
  is logged and swallowed, like `record_league_access`. A failed conditional put costs 1 WCU per
  open, which is negligible at this traffic. A read-before-write isn't worth the extra latency.

### 3. `GET /me/leagues` assembly
1. Query GSI4 `member_user_id = caller` (paginated). The canonical ID comes from the projected `PK`.
2. `BatchGetItem` the METADATA items in chunks of 100, retrying `UnprocessedKeys`.
3. Per league, reuse the existing GSI1 lookup that `get_league_seasons` uses. GSI1 projects
   `seasons` and `PK` (`LEAGUE#{league_id}#PLATFORM#{platform}`), so one query gives both the
   unified season list and the platform league IDs. Pick the lookup whose platform equals the
   effective platform and whose max season is highest. Ignore pending lookups (no `seasons`). Drop
   the league if there's no usable lookup or METADATA.
4. `espn_reauth_required` reuses `espn_credentials.get_reauth_status(caller)`, called at most once
   per request and only if some league qualifies (caller is owner, effective ESPN, auto-refresh on).
5. Sort by `updated_at = last_refresh_at or onboarded_at`, descending.

N GSI1 queries per request is fine because users have a handful of leagues. If that changes,
`league_id`/`seasons` could be denormalized onto the row later without changing the API.

The route sits under `/me` (`/me/leagues`) as a user-scoped resource. It uses the existing
`get_authenticated_user` dependency, which returns `401` when the session is missing.

### 4. Frontend
- `landing-page.tsx` gets `showMyLeagues` state. Toggling it clears `showConnectForm`, and the
  reverse. The button renders only when `isSignedIn`.
- New `my-leagues.tsx` (`MyLeaguesPanel`) fetches on mount (that is, on first expand), using
  `toResult` + the shared `<ErrorAlert>` for errors. The skeleton, empty, and list layouts follow
  the mockup with Tailwind/shadcn tokens. Logos reuse `@/assets/{espn,sleeper,yahoo}-logo.svg`.
- A row click calls `getLeague(league_id, platform)` → `setLeagueCookies(league_id, platform,
  seasons)` → `navigate('/home')`, the same steps as the existing onboarded-league connect path.
  The panel shows an inline error on failure.
- `getMyLeagues()` goes in `frontend/src/components/api/leagues.ts`, next to `getLeague`.
- "Updated X ago" uses the existing relative-time helper if there is one; otherwise a small local
  formatter.

### 5. Backfill
`scripts/utility_scripts/backfill_league_members.py`: query GSI3 for every METADATA item
(paginated). For each `owner_user_id` and each entry in `members`, do a conditional put of a row
with `joined_at = onboarded_at`. Prints counts of created and skipped rows. It's safe to re-run.

## Risks / Trade-offs

- [Index drifts from METADATA because of a partial API failure] → The listing only affects
  convenience, not access. Writes are idempotent, and the backfill script can be re-run.
- [An index row exists but access has since been revoked (no flow does this today)] → The row
  opens through `getLeague`, which still enforces the `403` member gate. The UI shows that inline.
- [GSI4 is eventually consistent] → A league can take about a second to appear after an invite
  is redeemed. That's acceptable, because the panel fetches when it opens.
- [Sleeper open writes add ~1 WCU per open] → Negligible. It's best-effort and never blocks the read.
- [Adding a GSI to the global table (primary + replica)] → GSI creation backfills online. Apply
  infra before the backend, so queries never hit a missing index.

## Migration Plan

1. Terraform: add the `member_user_id`/`joined_at` attribute definitions and GSI4 to
   `infrastructure/modules/dynamodb/main.tf`. Add the `index/GSI4` ARNs (primary + replica) to the
   API Lambda's DynamoDB policy in `infrastructure/global/{dev,prod}/main.tf`. Apply, and wait for GSI4
   to be `ACTIVE`. The regional apply also picks up the `/me/leagues` OpenAPI route.
2. Deploy the backend (API + onboarder).
3. Run the backfill script against prod.
4. Deploy the frontend.

Rollback: revert the frontend and backend. The leftover rows and GSI4 are harmless, and can be
dropped later.
