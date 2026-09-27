# frontend/connect-yahoo-league Specification

## Purpose
Add Yahoo as a selectable platform in the Connect League flow. Because Yahoo requires OAuth 2.0, onboarding a Yahoo league routes through an account-link redirect: the user picks Yahoo, enters their league id, and clicks Connect; the app hands off to Yahoo's consent screen and, on return, resumes onboarding. The OAuth handshake and token storage are backend-owned; this capability covers the UI. No Yahoo tokens ever reach the browser. A linked Yahoo league onboards for real through the same pipeline as ESPN and Sleeper.

## Requirements

### Requirement: Offer Yahoo as a connect platform
The Connect-League platform selector SHALL offer Yahoo alongside ESPN and Sleeper, with a league-id field (no ESPN cookie fields).

#### Scenario: Yahoo selected
- **WHEN** the user picks Yahoo in the platform selector
- **THEN** the form shows the league-id field and a Connect button, and no ESPN cookie fields

### Requirement: Start the OAuth link on Connect
Clicking Connect with Yahoo selected SHALL first attempt an in-place onboard (`POST /leagues` with `platform=YAHOO`) for the entered league id, and SHALL start Yahoo's consent handshake only when the caller has no stored Yahoo link. An already-linked caller onboards in place (no consent step); a `403` "link first" response starts the OAuth step via `GET /leagues/yahoo/oauth/authorize`. The consent screen SHALL open in a popup window (`display=popup`) so the connect page stays mounted with its progress indicator, and the app SHALL resume onboarding inline when the popup reports a successful link — falling back to a full-page redirect to the consent URL only when the browser blocks the popup.

#### Scenario: Already linked — no consent redirect
- **WHEN** the user selects Yahoo, enters a league id, and clicks Connect while already linked (the onboard call returns a `correlation_id` or a `200` null-`data` "already onboarded")
- **THEN** the league is onboarded in place and no Yahoo consent window is opened

#### Scenario: Begin consent
- **WHEN** the user selects Yahoo, enters a league id, and clicks Connect while not linked (the onboard call returns `403` "Link your Yahoo account first")
- **THEN** the form calls `GET /leagues/yahoo/oauth/authorize?leagueId=<id>&display=popup` and opens the returned Yahoo consent URL in a popup window, leaving the connect page mounted with its progress indicator

#### Scenario: Resume inline after the popup links
- **WHEN** the consent popup reports a successful link back to the opener (a linked result with a league id)
- **THEN** the app resumes onboarding for that league id inline (no page reload) and closes/stops tracking the popup

#### Scenario: Popup blocked falls back to redirect
- **WHEN** the browser blocks the consent popup (the window fails to open)
- **THEN** the app falls back to a full-page redirect to the Yahoo consent URL, and onboarding resumes on the return leg

#### Scenario: Consent popup dismissed
- **WHEN** the user closes the consent popup without completing the link
- **THEN** the form stops the loading state and shows an inline retry message rather than waiting indefinitely

### Requirement: Handle the OAuth return
Returning to the landing page `/?platform=YAHOO&yahooLinked=1` SHALL resume onboarding inline for the carried league id with the same hero progress UI used for ESPN/Sleeper; a league that is already onboarded SHALL route the user into their existing league dashboard rather than erroring; a declined/failed link SHALL show an inline retry alert with Yahoo preselected. The standalone `/connect_league` return page is retired: `/connect_league` SHALL forward any Yahoo return params to the landing page.

#### Scenario: Linked return
- **WHEN** the browser returns to the landing page `/` with `platform=YAHOO&yahooLinked=1` and a `leagueId`
- **THEN** the landing page auto-opens the connect form with Yahoo selected and resumes onboarding for that league id inline via `POST /leagues` with `platform=YAHOO`, polling the job to completion with the hero progress bar and navigating to `/home` on success

#### Scenario: Already onboarded league
- **WHEN** the return resumes onboarding and `POST /leagues` responds `200 "League already onboarded"` with a null `data` (the league already exists)
- **THEN** the page skips job polling and routes the user into their existing league dashboard (`/home`) rather than showing a generic error

#### Scenario: Declined or failed
- **WHEN** the return carries `yahooLinked=0`
- **THEN** an inline retry alert ("Yahoo linking was cancelled or failed — try again") is shown on the landing page with Yahoo preselected (no global banner, no separate error page)

#### Scenario: Return params forwarded from the retired page
- **WHEN** the browser lands on `/connect_league` with `platform=YAHOO` return params (e.g. an in-flight OAuth callback or a stale bookmark)
- **THEN** it redirects to the landing page `/` preserving the `platform`, `yahooLinked`, and `leagueId` params so the inline return handling runs

### Requirement: Onboard a linked Yahoo league
Onboarding a linked Yahoo league SHALL start onboarding via `POST /leagues` with `platform=YAHOO`
and poll the returned job to completion (the same success/progress/error flow used for ESPN and
Sleeper), and SHALL surface a "Reconnect your Yahoo account" prompt on a `YAHOO_AUTH` re-link
signal.

#### Scenario: Onboard and poll to completion
- **WHEN** a linked Yahoo league is submitted and the backend returns `201` with a `correlation_id`
- **THEN** the UI polls job status and shows progress, then the completed league on success and an
  inline error alert on a `FAILED` job — with no "coming soon" notice

#### Scenario: Expired/revoked link
- **WHEN** onboarding returns the `YAHOO_AUTH` re-link signal (at submit time or as a `FAILED` job)
- **THEN** the UI shows a "Reconnect your Yahoo account" prompt that restarts the OAuth step rather
  than a generic failure

### Requirement: Keep tokens out of the browser and respect demo mode
Yahoo access/refresh tokens SHALL never appear in the frontend, and connecting (and the OAuth redirect) SHALL be disabled/redirected in demo mode.

#### Scenario: No tokens in browser
- **WHEN** the Yahoo flow runs
- **THEN** no Yahoo access/refresh token appears in storage, state, or network responses (the frontend only observes link status via backend markers/endpoints)

#### Scenario: Demo mode
- **WHEN** the app is in demo mode
- **THEN** connecting a Yahoo league and the OAuth redirect are disabled/redirected

### Requirement: No auto-refresh opt-in for Yahoo leagues

The Yahoo connect flow SHALL NOT offer an automatic-refresh opt-in (Yahoo leagues are always
refreshed in season; backend/scheduled-league-auto-refresh), and the Yahoo onboard request SHALL NOT
carry an automatic-refresh opt-in choice. The connect form SHALL NOT show any auto-refresh checkbox
or note when Yahoo is selected.

#### Scenario: No opt-in shown for Yahoo

- **WHEN** the user selects Yahoo in the connect form
- **THEN** no "enable automatic weekly refresh" checkbox and no auto-refresh note are shown

#### Scenario: No opt-in sent with the Yahoo onboard

- **WHEN** the user connects a Yahoo league (in place, or after the consent popup/redirect)
- **THEN** the `POST /leagues` request for that Yahoo league carries no automatic-refresh opt-in
  choice