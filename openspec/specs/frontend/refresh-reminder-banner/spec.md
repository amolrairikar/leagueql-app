# refresh-reminder-banner Specification

## Purpose
A thin, non-dismissible banner below the in-app header that reminds an ESPN league's owner to refresh the league when its data is more than 7 days old, pointing them to the sidebar's "Refresh League" action. It auto-hides once the data is fresh again.

## Requirements

### Requirement: Show the reminder for stale ESPN leagues
The banner SHALL render below the in-app header on main-app pages when the current league is on the ESPN platform, the authenticated caller is the league owner, and the league's data is more than 7 days old. Data freshness SHALL be measured from `last_refresh_at` when present, falling back to `onboarded_at` when the league has never been refreshed. The message SHALL read: `Refresh your ESPN league data by clicking the "Refresh League" button in the sidebar!`

#### Scenario: Stale ESPN league, owner
- **WHEN** an ESPN league owner views a main-app page and the league's `last_refresh_at` (or `onboarded_at` if never refreshed) is more than 7 days ago
- **THEN** the banner appears below the header with the refresh reminder message

#### Scenario: Fresh ESPN league
- **WHEN** the league's freshness timestamp is 7 days ago or less
- **THEN** the banner does not appear

#### Scenario: Never-refreshed league falls back to onboarded_at
- **WHEN** the league has no `last_refresh_at` and its `onboarded_at` is more than 7 days ago
- **THEN** the banner appears

### Requirement: Restrict the reminder audience
The banner SHALL NOT render for Sleeper leagues, for non-owners, in demo mode, when no league is connected, or while the league's freshness is still loading.

#### Scenario: Sleeper league
- **WHEN** the current league is on the Sleeper platform
- **THEN** the banner does not appear regardless of freshness

#### Scenario: Non-owner viewer
- **WHEN** the caller is not the league owner
- **THEN** the banner does not appear

#### Scenario: Demo mode
- **WHEN** the app is in demo mode
- **THEN** the banner does not appear

#### Scenario: Freshness loading
- **WHEN** the league's freshness data has not yet loaded
- **THEN** the banner does not appear

### Requirement: Not dismissible
The banner SHALL NOT provide a dismiss control; it disappears only when the league's data becomes fresh again (within 7 days).

#### Scenario: No dismiss affordance
- **WHEN** the banner is shown
- **THEN** there is no close/X button and no per-browser dismissal is stored
