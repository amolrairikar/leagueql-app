## ADDED Requirements

### Requirement: Alert the owner when saved ESPN cookies were rejected

A non-dismissible banner SHALL render below the in-app header when the current league is an ESPN
league, the caller is the owner, and the league metadata reports `espn_reauth_required`. It SHALL
tell the owner that automatic refresh is paused because ESPN rejected their saved cookies and point
them to the sidebar's "Update ESPN Cookies" action. It SHALL NOT render in demo mode, with no
league connected, for non-ESPN leagues, for non-owners, or while league metadata is loading.

#### Scenario: Owner with rejected cookies
- **WHEN** the owner of an ESPN league views a main-app page and `espn_reauth_required` is true
- **THEN** the banner shows the paused-refresh message pointing at "Update ESPN Cookies", with no
  dismiss control

#### Scenario: Cookies healthy
- **WHEN** `espn_reauth_required` is false
- **THEN** the banner does not appear

#### Scenario: Non-owner or demo mode
- **WHEN** the caller is not the owner, or the app is in demo mode
- **THEN** the banner does not appear
