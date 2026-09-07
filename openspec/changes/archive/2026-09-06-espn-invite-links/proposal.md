## Why

Non-owners find it painful to join an already-onboarded **private ESPN** league: the only way to prove membership today is to submit their own `SWID`/`espn_s2` cookies to `POST /leagues/{id}/verify-membership`, which are fiddly to obtain (Chrome extension or manual copy). Users have asked for a way for the league owner to simply share a link with their leaguemates so nobody else has to deal with cookies.

## What Changes

- Add an owner-minted, reusable **invite link**. The owner mints a token; any leaguemate who opens the link and signs into LeagueQL is added to the league's `members` set — **no ESPN cookies required**.
- One reusable link per league with **no auto-expiry**; minting a new link overwrites the previous hash, which is the revocation mechanism.
- **BREAKING**: Remove the cookie-based `POST /leagues/{id}/verify-membership` flow entirely (endpoint, frontend `verifyMembership` client call, and the cookie-entry Join League dialog). After this change, the only ways a non-owner gains read access to a private ESPN league are an owner's invite link or an ownership-transfer token. (Existing stored `members` sets are unaffected; owner-side onboarding/refresh/migrate still use ESPN cookies, and the extension is unchanged.)
- New backend endpoints: `POST /leagues/{id}/invite-token` (owner-gated mint) and `POST /leagues/{id}/accept-invite` (any authenticated caller redeems). Store `invite_token_hash` on the league METADATA item.
- New frontend `/join/:leagueId` redemption page and an owner-side "invite link" dialog in the sidebar; rework `MembershipGuard`/landing/connect so a non-member is pointed to an invite link instead of a cookie form.

## Capabilities

### New Capabilities
<!-- none — invite links extend existing authorization and UI capabilities -->

### Modified Capabilities
- `backend/league-authorization`: replace the "Verify ESPN membership" (cookie) requirement with invite-link mint + redeem requirements.
- `frontend/ownership-transfer`: replace the cookie-based "Verify ESPN membership for non-members" requirement with owner-mint-invite-link and non-member "ask for an invite link" behavior.
- `frontend/connect-league`: the ownership/membership-aware routing no longer auto-verifies ESPN cookies on a `403`; a non-member is directed to an invite link instead.

## Impact

- **Backend:** `src/api/routes.py` (add mint + redeem, remove `verify_membership`), `src/api/main.py` (add `AcceptInvitePayload`), `src/api/helpers.py` (reuse `add_league_member`).
- **Frontend:** `frontend/src/components/api/leagues.ts`, new `frontend/src/features/ownership/invite-link-dialog.tsx` and `frontend/src/features/connect_league/join-invite-page.tsx`, `frontend/src/app/app.tsx` (route), `frontend/src/features/sidebar/app-sidebar.tsx`, `frontend/src/features/ownership/membership-guard.tsx`, `frontend/src/features/connect_league/join-league-dialog.tsx`, `frontend/src/features/connect_league/league-connect.tsx`, `frontend/src/features/landing_page/landing-page.tsx`.
- **Docs:** `docs/api/openapi_spec.yaml` (add two endpoints, remove `verify-membership`), `docs/db/dynamodb_spec.md` (add `invite_token_hash`, update `members` row).
- **Tests:** backend unit + component and frontend component tests added/updated; `verify-membership` tests removed.
- No new deployed infrastructure component (architecture diagram unchanged).
