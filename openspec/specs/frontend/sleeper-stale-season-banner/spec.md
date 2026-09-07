# frontend/sleeper-stale-season-banner Specification

## Purpose
A thin, non-dismissible banner below the in-app header that tells a Sleeper league's owner to
onboard the current season's league ID when the current fantasy season is after the league's
latest onboarded season. Because Sleeper links seasons backward-only, refreshing the existing
league can never surface the new season, so the owner must re-onboard from the landing page. It
auto-hides once a current-season league is onboarded.

## Requirements

### Requirement: Show the banner for stale-season Sleeper leagues
The banner SHALL render below the in-app header on main-app pages when the current league is on
the Sleeper platform, the authenticated caller is the league owner, and the current fantasy
season is greater than the league's latest onboarded season. The latest onboarded season SHALL
be the numeric maximum of the league's onboarded seasons. The current fantasy season SHALL be
computed from the local clock as the calendar year, minus one when the current month is before
September (month index less than 8). The message SHALL read: `Not seeing your current season's
data? Enter your latest season's league ID on the landing page.` and SHALL link "landing page"
to the landing route (`/`).

#### Scenario: Stale-season Sleeper league, owner
- **WHEN** a Sleeper league owner views a main-app page and the current fantasy season is after
  the league's latest onboarded season
- **THEN** the banner appears below the header with the message and a link to the landing page

#### Scenario: Up-to-date Sleeper league
- **WHEN** the league's latest onboarded season is greater than or equal to the current fantasy
  season
- **THEN** the banner does not appear

#### Scenario: Season flips in September
- **WHEN** the league's latest onboarded season is the prior calendar year and the current month
  is August (before September)
- **THEN** the banner does not appear, because the current fantasy season is still the prior year
- **WHEN** the current month reaches September of the current calendar year
- **THEN** the banner appears, because the current fantasy season has advanced past the league's
  latest onboarded season

### Requirement: Restrict the banner audience
The banner SHALL NOT render for ESPN leagues, for non-owners, in demo mode, when no league is
connected, when the league has no onboarded seasons, or while ownership is still loading.

#### Scenario: ESPN league
- **WHEN** the current league is on the ESPN platform
- **THEN** the banner does not appear regardless of its seasons

#### Scenario: Non-owner viewer
- **WHEN** the caller is not the league owner
- **THEN** the banner does not appear

#### Scenario: Demo mode
- **WHEN** the app is in demo mode
- **THEN** the banner does not appear

#### Scenario: No league connected
- **WHEN** no league is connected
- **THEN** the banner does not appear

#### Scenario: Ownership loading
- **WHEN** the league's ownership has not yet loaded
- **THEN** the banner does not appear

### Requirement: Not dismissible
The banner SHALL NOT provide a dismiss control; it disappears only when a league whose latest
onboarded season is at or beyond the current fantasy season is connected.

#### Scenario: No dismiss affordance
- **WHEN** the banner is shown
- **THEN** there is no close/X button and no per-browser dismissal is stored
