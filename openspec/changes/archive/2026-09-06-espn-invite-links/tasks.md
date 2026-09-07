## 1. Backend — endpoints

- [x] 1.1 Add `AcceptInvitePayload { token: str }` to `src/api/main.py` (alongside `ClaimOwnershipPayload`); verify it imports and `pipenv run ruff check` passes.
- [x] 1.2 Add `POST /leagues/{leagueId}/invite-token` in `src/api/routes.py` (owner-gated, Sleeper→`400`, mint `token_urlsafe(32)`, `SET invite_token_hash`, return plaintext once); modeled on `create_transfer_token`.
- [x] 1.3 Add `POST /leagues/{leagueId}/accept-invite` in `src/api/routes.py` (Sleeper→`400`, no hash→`404`, `hmac.compare_digest` mismatch→`403`, match→`add_league_member` and leave hash intact→`200`).
- [x] 1.4 Remove `POST /leagues/{leagueId}/verify-membership` from `src/api/routes.py`; confirm `EspnMembersPayload` is still used by `get_espn_members` and keep it.
- [x] 1.5 Backend unit tests in `tests/unit/api/` covering mint (owner-only `403`, Sleeper `400`, stores hash, regenerate overwrites) and redeem (valid adds member, second redeem still succeeds, wrong token `403`, no token `404`, Sleeper `400`); remove the `verify_membership` tests. Verify `pipenv run pytest tests/unit` passes with coverage near 100%.

## 2. Backend — component tests & docs

- [x] 2.1 Add/replace a `tests/component/` scenario: owner mints, a second user redeems, then that user's `GET /leagues/{id}` succeeds (crossing the `members` boundary); remove `verify-membership` component scenarios. Verify `pipenv run behave tests/component` passes.
- [x] 2.2 Update `docs/api/openapi_spec.yaml`: add `/leagues/{leagueId}/invite-token` and `/leagues/{leagueId}/accept-invite`, remove `/leagues/{leagueId}/verify-membership`.
- [x] 2.3 Update `docs/db/dynamodb_spec.md`: add `invite_token_hash` (String, optional) to the METADATA item and update the `members` row to reference invite links instead of `verify-membership`.

## 3. Frontend — API client & redemption

- [x] 3.1 In `frontend/src/components/api/leagues.ts` add `createInviteToken(leagueId, platform)` and `acceptInvite(leagueId, platform, token)`; remove `verifyMembership`. Verify `npm run lint` passes.
- [x] 3.2 Add `frontend/src/features/connect_league/join-invite-page.tsx` (reads `platform`/`invite` from `useSearchParams`, calls `acceptInvite` then `getLeague`, sets league cookies, navigates to `/home`; inline error on invalid/revoked token) and wire a `/join/:leagueId` route in `frontend/src/app/app.tsx`. (The page self-handles Clerk auth — signing in returns to the invite URL — rather than `ProtectedRoute`, which would redirect to `/` and drop the invite.)

## 4. Frontend — owner dialog & non-member UX

- [x] 4.1 Add `frontend/src/features/ownership/invite-link-dialog.tsx` (clone of `transfer-ownership-dialog.tsx`) that mints a link, shows the full `${origin}/join/...` URL with the Copy button and revoke note; trigger it from `frontend/src/features/sidebar/app-sidebar.tsx` as an owner-only "Invite Leaguemates" action.
- [x] 4.2 Rework the non-member path: `membership-guard.tsx` shows invite-link guidance (no cookie form) on `403`; repurpose or remove `join-league-dialog.tsx`; remove the `verifyMembership` auto-verify-on-`403` branches in `landing-page.tsx` and `league-connect.tsx`.

## 5. Frontend — component tests

- [x] 5.1 Add/update jest-cucumber specs under `frontend/src/features/**/__tests__/`: `join-invite-page` (valid `invite`→joins + routes home; invalid→error), invite dialog (create→copyable URL shown), `MembershipGuard` `403`→invite-link message; update connect/landing scenarios and remove the `JoinLeagueDialog` cookie tests. Verify `npm run test` passes.

## 6. Verify & format

- [x] 6.1 Run `pipenv run ruff check --fix . && pipenv run ruff format .` and `npm run format:fix && npm run lint`; run `openspec validate --all`. All green.
- [x] 6.2 End-to-end (dev server / `/run`): owner creates + copies an invite link; a second account opens it, signs in, lands on `/home` for the league and can read it; owner regenerates and the old link now errors on redeem.
