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
  History, Draft Recap, Draft Grades, Player Records, Matchup Records, and Analytics. The
  **Analytics** tab is a premium page ([FE-033](FE-033-analytics-page.md)) and is
  hidden when the `billing` master flag is off ([FE-026](FE-026-feature-flags.md)).
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
- **No page footer in the app layout:** the in-app pages do not render the marketing footer
  (About / Privacy / GitHub) — it was removed to reclaim vertical space on data-dense visual
  pages. The layout is a full-height (`h-svh`) flex column with the content region filling the
  inset; the marketing footer appears only on the public pages (landing, privacy, docs). The
  account menu still lives in the sidebar footer (desktop) / header (mobile).

## Acceptance Criteria
- [ ] The sidebar links to all eleven analytics pages and they route correctly. The Analytics
      page is premium and its nav item is hidden when `billing` is off.
- [ ] The sidebar exposes a refresh action pre-filled and locked to the current league, and
      surfaces cooldown/up-to-date/in-progress responses.
- [ ] The sidebar exposes a "Manage Subscription" item that opens the subscription dialog.
- [ ] The layout is responsive: the sidebar collapses and toggles on mobile.
- [ ] The demo banner appears in demo mode.
- [ ] The header wordmark links home and the theme toggle is present.
- [ ] The account menu (sign out) is reachable and functional on both desktop (sidebar footer)
      and mobile (header) — on mobile it is not rendered inside the modal sidebar sheet.
- [ ] The in-app app layout does not render the marketing page footer (it appears only on the
      public landing / privacy / docs pages).

## Authorization (FE-025)
Owner-only actions (Refresh, Migrate, Transfer Ownership, Manage Subscription, Delete) are gated on `is_owner` ([FE-025](FE-025-ownership-transfer-owner-gated-actions.md)); non-owners see View Another League and Claim Ownership.

## Sources
`src/features/sidebar/app-sidebar.tsx`, `src/features/sidebar/header-account.tsx`,
`src/app/app.tsx`, `src/hooks/use-mobile.ts`.
