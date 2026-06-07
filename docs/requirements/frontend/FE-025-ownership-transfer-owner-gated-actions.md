# FE-025: Ownership Transfer & Owner-Gated Actions

## Description
Surfaces league ownership in the UI ([BE-016](../backend/BE-016-league-ownership-authorization.md)):
it gates owner-only sidebar actions to the owner, points non-owners at the owner for billing,
gives non-owners an ESPN membership-verification path, and adds the ownership transfer/claim flow.

- **Owner state.** `useIsOwner` (`frontend/src/features/ownership/use-is-owner.ts`) reads the
  current league's `is_owner` from `getLeague()`. Demo / no-league bypass the fetch; a failed
  request resolves to non-owner so owner actions stay hidden.
- **Owner-gated sidebar.** `app-sidebar.tsx` renders **Refresh**, **Migrate**, **Transfer
  Ownership**, **Manage Subscription**, and **Delete** only when `is_owner`. Non-owners still see
  **View Another League** and a **Claim Ownership** entry. (Demo mode keeps its own branch.)
- **Non-owner paywall.** `subscription-required.tsx` shows the **Subscribe** CTA only to the
  owner; a non-owner sees "ask the league owner to subscribe" instead of a dead-end button.
- **ESPN membership verification.** `MembershipGuard`
  (`frontend/src/features/ownership/membership-guard.tsx`) wraps the analytics layout. When
  `getLeague` returns `403` for an ESPN league, it shows a **Verify your ESPN league membership**
  backdrop and opens the shared **Join League** dialog
  (`features/connect_league/join-league-dialog.tsx`) — the single membership-verification UI used
  across entry points (FE-002). The caller supplies cookies (extension autofill or manual entry)
  and the dialog posts them to `verify-membership`; on success the guard clears the API cache and
  re-renders the page in place (via the dialog's `onJoined` callback, instead of its default
  set-cookies-and-navigate), and a `403` from verify shows "We couldn't confirm you're in this
  ESPN league." Sleeper leagues never hit this.
- **Transfer / claim.** `TransferOwnershipDialog` (owner) mints a one-time token and copies it;
  `ClaimOwnershipDialog` (recipient) redeems a token and reloads league state on success. Both
  reuse the shared dialog + `<ErrorAlert>` patterns.
- **403 handling.** The mutating call sites already surface `ApiError` inline via `toResult` +
  `<ErrorAlert>`; a `403` reads as an owner-only / membership message rather than a generic error.

## Scope
- `frontend/src/features/ownership/` — `use-is-owner.ts`, `membership-guard.tsx`,
  `transfer-ownership-dialog.tsx`, `claim-ownership-dialog.tsx`.
- `frontend/src/features/sidebar/app-sidebar.tsx` — owner-gated actions + transfer/claim entries.
- `frontend/src/features/subscription/subscription-required.tsx` — non-owner paywall copy.
- `frontend/src/components/api/types.ts` (`is_owner`), `frontend/src/components/api/leagues.ts`
  (`verifyMembership`, `createTransferToken`, `claimOwnership`).
- `frontend/src/app/app.tsx` — `MembershipGuard` wraps the analytics layout (outside the
  `SubscriptionGuard`).

## Edge Cases
- **Loading owner state:** owner-only actions are hidden until `getLeague` resolves (no flash of
  actions for a non-owner).
- **Demo / no league:** owner gating is bypassed (demo uses its own sidebar branch); the
  membership guard renders children.
- **Fail-open membership guard:** a non-403 `getLeague` failure renders the page (the backend
  remains the source of truth); only a `403` shows the verification backdrop + Join dialog.
- **Extension missing / not logged in:** the Join dialog's autofill surfaces the existing
  "Could not reach the ESPN extension" / "Log into ESPN" guidance, and manual cookie entry
  remains available as a fallback.
- **Verify rejected:** ESPN-rejected cookies show "We couldn't confirm you're in this ESPN league."
- **Token copy:** the transfer token is shown once and copyable; closing the dialog clears it.
- **Claim success:** clears the API cache and reloads so the new owner immediately sees owner
  actions.

## Acceptance Criteria
- [ ] The sidebar shows Refresh / Migrate / Transfer Ownership / Manage Subscription / Delete only
      when the caller is the owner; non-owners see View Another League and Claim Ownership.
- [ ] The expired-subscription paywall shows Subscribe only to the owner; non-owners see the
      "ask the league owner to subscribe" message.
- [ ] An ESPN league that returns `403` shows the "Verify your ESPN league membership" prompt;
      a successful verify reveals the dashboard, and a rejected verify shows the inline error.
- [ ] The owner can mint a transfer token; a recipient can redeem it via the claim dialog.
- [ ] A `403` on a mutating endpoint renders a clear owner-only message inline.

## Sources
`src/features/ownership/`, `src/features/sidebar/app-sidebar.tsx`,
`src/features/subscription/subscription-required.tsx`, `src/components/api/{types,leagues}.ts`,
`src/app/app.tsx`.
