# FE-014: Navigation Sidebar & App Layout

## Description
The collapsible app sidebar and surrounding layout shared by all in-app pages. Provides
navigation to every analytics feature, a refresh entry point for the current league, a
"Manage Subscription" entry point, and the demo-mode banner. The header shows the LeagueQL
wordmark and theme toggle.

## Scope
- Layout: `AppLayout` in `src/app/app.tsx`; sidebar `src/features/sidebar/app-sidebar.tsx`;
  API in `src/features/sidebar/api-calls.ts`.
- Nav items: Home, Standings, Matchups, Playoff Bracket, Manager Comparison, Manager
  History, Draft Recap, Draft Grades, Player Records, Matchup Records.
- Settings items include "Manage Subscription", which opens the subscription dialog
  ([FE-021](FE-021-subscription-access-control.md)).

## Edge Cases
- **Refresh from sidebar:** the refresh form is pre-filled and locked to the league the user
  is currently viewing ([BE-002](../backend/BE-002-league-refresh.md)).
- **Refresh cooldown / up-to-date / in-progress:** surface the backend `429`/`409` responses.
- **Mobile:** sidebar collapses; `SidebarTrigger` toggles it (`use-mobile` hook).
- **Account menu placement:** the Clerk `UserButton` (account + sign out) lives in the sidebar
  footer on desktop. On mobile the sidebar is a modal sheet that locks `pointer-events` outside
  its content, and Clerk's dropdown portals outside the sheet — so its taps (including "Sign
  out") would fall through to the sidebar links beneath. To keep sign-out working, the account
  menu renders in the always-present header on mobile (`HeaderAccount`) instead of the sheet
  ([FE-019](FE-019-authentication.md)).
- **Demo mode:** show the demo banner; refresh/connect actions adjust accordingly
  ([FE-015](FE-015-demo-mode.md)).
- **No league connected:** navigation behaves sensibly when there's no active league.
- **Footer is fixed-height and bottom-pinned:** the layout is a full-height flex column; the
  content region grows to fill (`flex-1`) and the footer is `shrink-0`, so the footer keeps a
  constant height pinned to the bottom regardless of the content state — full dashboard, the
  subscription paywall, or the loading/activating spinner all fill the area the same way (so the
  footer never shifts or compresses between states).

## Acceptance Criteria
- [ ] The sidebar links to all ten analytics pages and they route correctly.
- [ ] The sidebar exposes a refresh action pre-filled and locked to the current league, and
      surfaces cooldown/up-to-date/in-progress responses.
- [ ] The sidebar exposes a "Manage Subscription" item that opens the subscription dialog.
- [ ] The layout is responsive: the sidebar collapses and toggles on mobile.
- [ ] The demo banner appears in demo mode.
- [ ] The header wordmark links home and the theme toggle is present.
- [ ] The account menu (sign out) is reachable and functional on both desktop (sidebar footer)
      and mobile (header) — on mobile it is not rendered inside the modal sidebar sheet.
- [ ] The footer stays a constant height pinned to the bottom of the viewport across content
      states (dashboard, paywall, loading) — it does not shift or resize.

## Authorization (FE-025)
Owner-only actions (Refresh, Migrate, Transfer Ownership, Manage Subscription, Delete) are gated on `is_owner` ([FE-025](FE-025-ownership-transfer-owner-gated-actions.md)); non-owners see View Another League and Claim Ownership.

## Sources
`src/features/sidebar/app-sidebar.tsx`, `src/features/sidebar/header-account.tsx`,
`src/app/app.tsx`, `src/hooks/use-mobile.ts`.
