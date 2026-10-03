## ADDED Requirements

### Requirement: Update ESPN cookies when auto-refresh credentials are rejected

When the owner views an auto-refresh-enabled ESPN league whose metadata reports
`espn_reauth_required`, the sidebar SHALL show an "Update ESPN Cookies" action alongside Turn Off
Auto-Refresh. It SHALL open the refresh dialog with the "enable automatic weekly refresh" opt-in
pre-checked, so submitting valid cookies re-stores them (on a successful refresh or an opted-in
`409`/`429` block) and resumes automatic refresh.

#### Scenario: Rejected cookies show the action
- **WHEN** the owner views an ESPN league whose `auto_refresh_enabled` and `espn_reauth_required`
  are both true
- **THEN** the sidebar shows "Update ESPN Cookies", and opening it shows the refresh dialog with the
  auto-refresh opt-in checked

#### Scenario: Healthy cookies hide the action
- **WHEN** the owner views an auto-refresh-enabled ESPN league whose `espn_reauth_required` is false
- **THEN** "Update ESPN Cookies" is not shown
