# navigation-sidebar Specification

## Purpose
The collapsible app sidebar and surrounding layout shared by all in-app pages. It provides navigation to every analytics feature, a refresh entry point for the current league, the demo-mode banner, and the account menu. The header shows the LeagueQL wordmark and theme toggle.

## Requirements

### Requirement: Navigate to all analytics pages
The sidebar SHALL link to all ten analytics pages and route to them correctly, with a header wordmark linking home and a theme toggle present.

#### Scenario: Navigation
- **WHEN** the user opens the sidebar
- **THEN** it links to Home, Standings, Matchups, Playoff Bracket, Manager Comparison, Manager History, Draft Recap, Draft Grades, Player Records, and Matchup Records, each routing correctly, with the header wordmark linking home and the theme toggle present

### Requirement: Refresh the current league
The sidebar SHALL expose a refresh action, shown only for ESPN leagues that are not enrolled in
auto-refresh (`auto_refresh_enabled` false or absent). Triggering it SHALL open an in-dashboard
dialog (not a separate page) in which the owner enters their ESPN `swid`/`espn_s2` cookies —
autofilled by the Chrome extension when present, or entered manually with the same per-field
tooltips — and the league is refreshed in place via `POST /leagues` (`requestType=REFRESH`). The
dialog SHALL also present an "enable automatic weekly refresh" opt-in checkbox (defaulting off,
since the action only appears for a not-yet-enrolled league); when checked, the opt-in SHALL be
sent with the refresh so the league enrolls in scheduled auto-refresh. The season SHALL be derived
automatically (frontend/connect-league) and never entered. ESPN cookies SHALL be transmitted once
and cleared from the browser on success; the dialog SHALL surface the backend
cooldown/up-to-date/in-progress (`429`/`409`) responses as a benign notice and refresh the
dashboard's data on success. When the refresh opted into automatic refresh and is blocked with a
`429`/`409` (the backend enrolls the league anyway, backend/league-refresh), the dialog SHALL
confirm that automatic refresh is now enabled, clear the ESPN cookies from the browser, and reload
into the enrolled state when closed; a `400` (cookies rejected by ESPN) SHALL surface the backend
message as an error.

#### Scenario: Sidebar refresh
- **WHEN** an ESPN league owner of a league not enrolled in auto-refresh triggers the sidebar refresh
- **THEN** an in-dashboard dialog opens with SWID/espn_s2 inputs (extension autofill or manual entry with tooltips) and an "enable automatic weekly refresh" opt-in defaulting off, the season is derived automatically, and on submit the league is refreshed in place without navigating to a separate connect/refresh page

#### Scenario: Enroll in auto-refresh from the dialog
- **WHEN** the owner checks "enable automatic weekly refresh" in the dialog and submits
- **THEN** the opt-in is included in the `POST /leagues` refresh request so the league enrolls in scheduled auto-refresh

#### Scenario: Refresh cooldown surfaced in the dialog
- **WHEN** the refresh submit returns `429` (weekly cooldown) or `409` (already up to date / in progress)
- **THEN** the dialog surfaces the backend message as a benign notice and does not treat it as a failure

#### Scenario: Opted-in refresh blocked but auto-refresh enabled
- **WHEN** the owner checks "enable automatic weekly refresh", submits, and the refresh returns `429` or `409`
- **THEN** the dialog shows an "Automatic refresh enabled" notice with the backend message, replaces its actions with a Done button, and on close reloads so the sidebar shows Turn Off Auto-Refresh instead of Refresh League

#### Scenario: Opted-in refresh with rejected cookies
- **WHEN** an opted-in refresh returns `400` because ESPN rejected the cookies
- **THEN** the dialog shows the backend message as an error and does not reload

#### Scenario: No refresh for Sleeper
- **WHEN** the sidebar renders for a Sleeper league
- **THEN** the Refresh League action is not shown (Sleeper leagues refresh automatically), even for the owner

#### Scenario: No refresh for auto-refresh-enabled ESPN leagues
- **WHEN** the sidebar renders for an ESPN league whose `auto_refresh_enabled` is true
- **THEN** the Refresh League action is not shown (the league refreshes automatically on a schedule), even for the owner

### Requirement: Responsive layout with reachable account menu
The layout SHALL be responsive (sidebar collapses/toggles on mobile), and the account menu (sign out) SHALL be reachable on both desktop (sidebar footer) and mobile (header), never inside the modal sidebar sheet.

#### Scenario: Mobile collapse
- **WHEN** the app is viewed on mobile
- **THEN** the sidebar collapses and toggles via `SidebarTrigger`

#### Scenario: Account menu placement
- **WHEN** the account menu is rendered
- **THEN** it appears in the sidebar footer on desktop and in the always-present header on mobile (not inside the modal sheet), so "Sign out" is reachable and functional

### Requirement: Demo banner and no marketing footer
The demo banner SHALL appear in demo mode, and the in-app layout SHALL NOT render the marketing footer.

#### Scenario: Demo banner
- **WHEN** demo mode is active
- **THEN** the demo banner appears on in-app pages

#### Scenario: No marketing footer
- **WHEN** an in-app page renders
- **THEN** the marketing footer (About / Privacy / GitHub) is not shown (it appears only on public pages)

### Requirement: Owner-gated sidebar actions
Owner-only actions SHALL be gated on `is_owner`, with non-owners seeing the alternate actions.
Invite Leaguemates SHALL additionally be gated on the league being an ESPN league, Refresh League
SHALL additionally be gated on the league being an ESPN league that is not enrolled in auto-refresh,
and Turn Off Auto-Refresh SHALL additionally be gated on the league being an ESPN league that is
enrolled in auto-refresh.

#### Scenario: Owner vs non-owner actions
- **WHEN** the sidebar renders for a league
- **THEN** Migrate, Transfer Ownership, and Delete are shown only when `is_owner` is true, Invite Leaguemates is shown only when `is_owner` is true and the league is an ESPN league, Refresh League is shown only when `is_owner` is true and the league is an ESPN league whose `auto_refresh_enabled` is false, Turn Off Auto-Refresh is shown only when `is_owner` is true and the league is an ESPN league whose `auto_refresh_enabled` is true, and non-owners see View Another League and Claim Ownership instead

### Requirement: Disable auto-refresh from the sidebar
The sidebar SHALL let the owner of an auto-refresh-enrolled ESPN league turn scheduled auto-refresh
off via a Turn Off Auto-Refresh action that opens a confirmation dialog and, on confirmation, calls
`PUT /leagues/{leagueId}/auto-refresh` with `enabled=false`. The dialog SHALL warn that the league
will stop refreshing automatically and that the stored ESPN login may be removed (requiring cookies
to be re-entered to opt back in). On success the league SHALL no longer be enrolled, restoring the
manual Refresh League action; on failure an inline error SHALL be surfaced and the dialog SHALL stay
open.

#### Scenario: Owner turns auto-refresh off
- **WHEN** the owner of an ESPN league whose `auto_refresh_enabled` is true confirms Turn Off Auto-Refresh
- **THEN** the app sends `PUT /leagues/{leagueId}/auto-refresh` with `enabled=false`, and on success the league is no longer enrolled and the manual Refresh League action is shown again

#### Scenario: Owner cancels
- **WHEN** the owner opens the Turn Off Auto-Refresh dialog and cancels
- **THEN** no request is sent and `auto_refresh_enabled` is unchanged

#### Scenario: Disable fails
- **WHEN** the `PUT /leagues/{leagueId}/auto-refresh` request fails
- **THEN** an inline error is shown, the dialog stays open, and the league remains enrolled

### Requirement: Export league data action
The sidebar SHALL show an "Export League Data" action to every league member (not gated on
`is_owner`) for a connected, non-demo league. Activating it SHALL open the export dialog
(frontend/export-league-data).

#### Scenario: Export action visible to members
- **WHEN** the sidebar renders for a connected league (owner or non-owner member, any platform)
- **THEN** an "Export League Data" action is shown

#### Scenario: Export action opens the dialog
- **WHEN** the "Export League Data" action is activated
- **THEN** the export dialog opens
