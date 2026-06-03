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
- **Demo mode:** show the demo banner; refresh/connect actions adjust accordingly
  ([FE-015](FE-015-demo-mode.md)).
- **No league connected:** navigation behaves sensibly when there's no active league.

## Acceptance Criteria
- [ ] The sidebar links to all ten analytics pages and they route correctly.
- [ ] The sidebar exposes a refresh action pre-filled and locked to the current league, and
      surfaces cooldown/up-to-date/in-progress responses.
- [ ] The sidebar exposes a "Manage Subscription" item that opens the subscription dialog.
- [ ] The layout is responsive: the sidebar collapses and toggles on mobile.
- [ ] The demo banner appears in demo mode.
- [ ] The header wordmark links home and the theme toggle is present.

## Sources
`src/features/sidebar/app-sidebar.tsx`, `src/app/app.tsx`, `src/hooks/use-mobile.ts`.
