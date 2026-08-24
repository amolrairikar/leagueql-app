# connect-yahoo-league Specification

## Purpose
Add Yahoo as a selectable platform in the Connect League flow. Because Yahoo requires OAuth 2.0, onboarding a Yahoo league is a two-step experience: the user first links their Yahoo account (OAuth consent), then selects/enters the Yahoo league to onboard. The OAuth handshake and token storage are backend-owned; this capability covers the UI. No Yahoo tokens ever reach the browser.

## Requirements

### Requirement: Gate onboarding on account linking
Selecting platform Yahoo while unlinked SHALL show a "Connect your Yahoo account" CTA in place of the ESPN cookie fields and disable onboard submit until linked.

#### Scenario: Unlinked Yahoo
- **WHEN** the user picks Yahoo and has no active link
- **THEN** the form shows a "Connect your Yahoo account" CTA instead of the ESPN cookie fields and disables onboard submit until linked

### Requirement: Start the OAuth link
The CTA SHALL call `GET /auth/yahoo/authorize` and navigate the browser (full-page redirect) to the returned Yahoo consent URL.

#### Scenario: Begin consent
- **WHEN** the user clicks the connect-account CTA
- **THEN** the form calls `GET /auth/yahoo/authorize` and navigates the browser to the returned Yahoo consent URL

### Requirement: Handle the OAuth return
Returning to `/connect_league?platform=YAHOO&yahooLinked=1` SHALL show the linked state, reveal league selection, and strip the marker params; a declined/failed link SHALL show an inline retry alert.

#### Scenario: Linked return
- **WHEN** the browser returns with `platform=YAHOO&yahooLinked=1`
- **THEN** the form restores to Yahoo, shows the "Yahoo account connected" state, advances to league selection, and strips the marker params from the URL

#### Scenario: Declined or failed
- **WHEN** the callback returns a declined/failed marker
- **THEN** an inline retry alert ("Yahoo linking was cancelled or failed — try again") is shown with a retry CTA (no global banner, no hard error page)

### Requirement: Select and onboard a Yahoo league
Once linked, the user SHALL select a Yahoo league (a dropdown of their leagues, with a manual league-key fallback) and onboard via `POST /leagues?requestType=ONBOARD` with `platform=YAHOO`, then poll to completion like the standard connect flow.

#### Scenario: League selection
- **WHEN** the account is linked
- **THEN** the user selects a league from a dropdown of their Yahoo leagues (falling back to a manual league-key field if the listing is unavailable), showing an empty-state when the account has no eligible leagues

#### Scenario: Onboard and poll
- **WHEN** a Yahoo league is submitted
- **THEN** it onboards via `POST /leagues` with `platform=YAHOO`, polls `GET /jobs/{jobId}` through slow (~120s) jobs showing in-progress/success/failure with the backend `failure_reason`, clears the API cache, and routes into the app on success

### Requirement: Reconnect on re-link signal
A backend `YAHOO_AUTH` re-link signal SHALL surface a "Reconnect your Yahoo account" prompt that restarts the OAuth step.

#### Scenario: Expired/revoked link
- **WHEN** onboarding/refresh (or a leagues listing) returns the `YAHOO_AUTH` re-link signal
- **THEN** the UI shows a "Reconnect your Yahoo account" prompt that restarts the OAuth step rather than a generic failure

### Requirement: Keep tokens out of the browser and respect demo mode
Yahoo access/refresh tokens SHALL never appear in the frontend, and connecting (and the OAuth redirect) SHALL be disabled/redirected in demo mode. Ownership handling matches the standard connect flow.

#### Scenario: No tokens in browser
- **WHEN** the Yahoo flow runs
- **THEN** no Yahoo access/refresh token appears in storage, state, or network responses (the frontend only observes link status via backend markers/endpoints)

#### Scenario: Demo mode
- **WHEN** the app is in demo mode
- **THEN** connecting a Yahoo league and the OAuth redirect are disabled/redirected
