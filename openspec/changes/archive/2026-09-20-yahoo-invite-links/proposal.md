## Why

LeagueQL's owner-minted invite links let a leaguemate gain read access to a private league
without submitting their own platform credentials — but they only work for ESPN. Yahoo leagues
are gated by the same `require_league_member` read boundary (everything but Sleeper is gated), yet
a Yahoo leaguemate has no way to become a member: a non-owner gets a `403` from `getLeague` with
no path forward. The invite mechanism is already platform-agnostic at the data layer (`members`
set + `invite_token_hash` on METADATA, `add_league_member`), so closing this gap is a matter of
lifting the ESPN-only guards rather than building anything new.

## What Changes

- Enable the existing invite-link mint/redeem flow for **Yahoo** leagues, treating the two gated
  platforms (ESPN and Yahoo) uniformly and rejecting only **Sleeper** (whose reads are open).
- **Backend**: broaden the `platform != ESPN` guards in `create_invite_token` and `accept_invite`
  to reject only Sleeper (`400`).
- **Frontend**: un-gate the sidebar "Invite Leaguemates" owner action, the `/join` redemption
  page's validity check, and the `MembershipGuard` private-league guidance so they cover Yahoo;
  generalize ESPN-specific copy in the invite dialog, join page, and membership guard to
  platform-neutral wording.
- Generalize the affected requirements/scenarios and keep docs (`openapi_spec.yaml`,
  `dynamodb_spec.md`) in sync.
- No data-model change and no new endpoint; a Yahoo invitee still needs no Yahoo credentials of
  their own (the owner's linked token onboards the data).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/league-authorization`: generalize the invite mint/redeem requirements from ESPN-only
  to gated platforms (ESPN and Yahoo); only Sleeper is rejected with `400`.
- `frontend/ownership-transfer`: generalize the "share an invite link", "redeem an invite link",
  and "non-member read directs to an invite link" requirements to cover Yahoo as well as ESPN.
- `frontend/connect-league`: generalize the ownership/membership-aware routing so a non-member of
  a gated league (ESPN or Yahoo) is directed to an invite link.

## Impact

- Backend: `src/api/routes.py` (`create_invite_token`, `accept_invite`).
- Frontend: `features/sidebar/app-sidebar.tsx`, `features/connect_league/join-invite-page.tsx`,
  `features/ownership/invite-link-dialog.tsx`, `features/ownership/membership-guard.tsx`, and the
  non-member guidance in `features/connect_league/league-connect.tsx` /
  `features/landing_page/landing-page.tsx`.
- Docs: `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md`.
- Tests: backend unit (`tests/unit/api/test_endpoints.py`), backend component
  (`tests/component/features/league_ownership.feature` + steps), frontend component
  (`ownership/__tests__/invite-link.*`, `connect_league/__tests__/join-invite.*`,
  `ownership/__tests__/membership-guard.*`).
- No breaking changes: ESPN behavior is unchanged; Sleeper still returns `400`.
