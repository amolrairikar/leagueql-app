# informational-banner Specification

## Purpose
A thin, generic informational banner rendered below the in-app header, used to promote the current campaign (a Discord community invite today). It is gated behind the `banner` global feature flag so it can be toggled from the SSM console with no redeploy, and it is dismissible per-browser via `localStorage`. Its content is a single editable config block, so refreshing the campaign is a content change.

## Requirements

### Requirement: Gate the banner on the feature flag
The banner SHALL render nothing when the `banner` flag is off, and appear below the header on every main-app page when the flag is on (linking to the campaign URL in a new tab when configured).

#### Scenario: Flag off
- **WHEN** the `banner` flag is off
- **THEN** the banner renders nothing anywhere, regardless of dismissal state

#### Scenario: Flag on
- **WHEN** the `banner` flag is on and not dismissed
- **THEN** the banner shows below the header on every main-app page with its message and, when `BANNER_LINK_URL` is set, a link opening in a new tab (`rel="noopener noreferrer"`); an empty link URL renders the label as plain text

### Requirement: Restrict to the main app and hide in demo
The banner SHALL NOT render on public marketing routes, and SHALL be suppressed in demo mode even with the flag on.

#### Scenario: Public routes
- **WHEN** a landing/docs/privacy/changelog route renders
- **THEN** the banner does not appear

#### Scenario: Demo mode
- **WHEN** the app is in demo mode
- **THEN** the banner renders nothing even with the flag on

### Requirement: Persist dismissal per browser
Dismissing the banner SHALL hide it and keep it hidden after a reload via `localStorage`, tolerating storage failures.

#### Scenario: Dismiss persists
- **WHEN** the user clicks the close (X) button
- **THEN** the banner hides and writes `leagueql.bannerDismissed`, staying hidden across reloads/navigations for that browser

#### Scenario: Storage unavailable
- **WHEN** `localStorage` read/write fails (private browsing, disabled storage)
- **THEN** the failure is swallowed and the banner still renders and dismisses for the session
