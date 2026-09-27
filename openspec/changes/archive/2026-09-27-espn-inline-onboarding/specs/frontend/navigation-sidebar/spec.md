## MODIFIED Requirements

### Requirement: Refresh the current league
The sidebar SHALL expose a refresh action, shown only for ESPN leagues that are not enrolled in
auto-refresh (`auto_refresh_enabled` false or absent). Triggering it SHALL open an in-dashboard
dialog (not a separate page) in which the owner enters their ESPN `swid`/`espn_s2` cookies —
autofilled by the Chrome extension when present, or entered manually with the same per-field
tooltips — and the league is refreshed in place via `POST /leagues` (`requestType=REFRESH`). The
season SHALL be derived automatically (frontend/connect-league) and never entered. ESPN cookies
SHALL be transmitted once and cleared from the browser on success; the dialog SHALL surface the
backend cooldown/up-to-date/in-progress (`429`/`409`) responses as a benign notice and refresh the
dashboard's data on success.

#### Scenario: Sidebar refresh
- **WHEN** an ESPN league owner of a league not enrolled in auto-refresh triggers the sidebar refresh
- **THEN** an in-dashboard dialog opens with SWID/espn_s2 inputs (extension autofill or manual entry with tooltips), the season is derived automatically, and on submit the league is refreshed in place without navigating to a separate connect/refresh page

#### Scenario: Refresh cooldown surfaced in the dialog
- **WHEN** the refresh submit returns `429` (weekly cooldown) or `409` (already up to date / in progress)
- **THEN** the dialog surfaces the backend message as a benign notice and does not treat it as a failure

#### Scenario: No refresh for Sleeper
- **WHEN** the sidebar renders for a Sleeper league
- **THEN** the Refresh League action is not shown (Sleeper leagues refresh automatically), even for the owner

#### Scenario: No refresh for auto-refresh-enabled ESPN leagues
- **WHEN** the sidebar renders for an ESPN league whose `auto_refresh_enabled` is true
- **THEN** the Refresh League action is not shown (the league refreshes automatically on a schedule), even for the owner
