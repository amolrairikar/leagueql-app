## MODIFIED Requirements

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
