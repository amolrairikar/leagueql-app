## Purpose
Add Yahoo as a selectable platform in the Connect League flow. Because Yahoo requires OAuth 2.0, onboarding a Yahoo league routes through an account-link redirect: the user picks Yahoo, enters their league id, and clicks Connect; the app hands off to Yahoo's consent screen and, on return, resumes onboarding. The OAuth handshake and token storage are backend-owned; this capability covers the UI. No Yahoo tokens ever reach the browser. This increment ships the linking round-trip; actual Yahoo league onboarding surfaces a "coming soon" state until the data client lands.

## ADDED Requirements

### Requirement: Offer Yahoo as a connect platform
The Connect-League platform selector SHALL offer Yahoo alongside ESPN and Sleeper, with a league-id field (no ESPN cookie fields).

#### Scenario: Yahoo selected
- **WHEN** the user picks Yahoo in the platform selector
- **THEN** the form shows the league-id field and a Connect button, and no ESPN cookie fields

### Requirement: Start the OAuth link on Connect
Clicking Connect with Yahoo selected SHALL call `GET /leagues/yahoo/oauth/authorize` with the entered league id and navigate the browser (full-page redirect) to the returned Yahoo consent URL.

#### Scenario: Begin consent
- **WHEN** the user selects Yahoo, enters a league id, and clicks Connect
- **THEN** the form calls `GET /leagues/yahoo/oauth/authorize?leagueId=<id>` and navigates the browser to the returned Yahoo consent URL

### Requirement: Handle the OAuth return
Returning to `/connect_league?platform=YAHOO&yahooLinked=1` SHALL show the linked state and resume onboarding for the carried league id; a declined/failed link SHALL show an inline retry alert.

#### Scenario: Linked return
- **WHEN** the browser returns to `/connect_league` with `platform=YAHOO&yahooLinked=1` and a `leagueId`
- **THEN** the page shows a "Yahoo account connected" state and resumes onboarding for that league id via `POST /leagues` with `platform=YAHOO`

#### Scenario: Declined or failed
- **WHEN** the return carries `yahooLinked=0`
- **THEN** an inline retry alert ("Yahoo linking was cancelled or failed — try again") is shown with a retry CTA (no global banner, no hard error page)

### Requirement: Surface onboarding and re-link states
Onboarding a linked Yahoo league SHALL surface the backend signals: a "coming soon" notice while the data client is unshipped, and a "Reconnect your Yahoo account" prompt on a `YAHOO_AUTH` re-link signal.

#### Scenario: Coming soon
- **WHEN** a linked Yahoo league is submitted and the backend returns the "coming soon" signal
- **THEN** the UI shows a neutral "Yahoo onboarding is coming soon" notice, not an error

#### Scenario: Expired/revoked link
- **WHEN** onboarding returns the `YAHOO_AUTH` re-link signal
- **THEN** the UI shows a "Reconnect your Yahoo account" prompt that restarts the OAuth step rather than a generic failure

### Requirement: Keep tokens out of the browser and respect demo mode
Yahoo access/refresh tokens SHALL never appear in the frontend, and connecting (and the OAuth redirect) SHALL be disabled/redirected in demo mode.

#### Scenario: No tokens in browser
- **WHEN** the Yahoo flow runs
- **THEN** no Yahoo access/refresh token appears in storage, state, or network responses (the frontend only observes link status via backend markers/endpoints)

#### Scenario: Demo mode
- **WHEN** the app is in demo mode
- **THEN** connecting a Yahoo league and the OAuth redirect are disabled/redirected
