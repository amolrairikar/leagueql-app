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
Clicking Connect with Yahoo selected SHALL first attempt an in-place onboard (`POST /leagues` with `platform=YAHOO`) for the entered league id, and SHALL redirect the browser to Yahoo's consent screen only when the caller has no stored Yahoo link. An already-linked caller onboards in place (no consent redirect); a `403` "link first" response triggers the OAuth redirect via `GET /leagues/yahoo/oauth/authorize`.

#### Scenario: Already linked — no consent redirect
- **WHEN** the user selects Yahoo, enters a league id, and clicks Connect while already linked (the onboard call returns a `correlation_id` or a `200` null-`data` "already onboarded")
- **THEN** the league is onboarded in place and the browser is NOT redirected to Yahoo's consent screen

#### Scenario: Begin consent
- **WHEN** the user selects Yahoo, enters a league id, and clicks Connect while not linked (the onboard call returns `403` "Link your Yahoo account first")
- **THEN** the form calls `GET /leagues/yahoo/oauth/authorize?leagueId=<id>` and navigates the browser (full-page redirect) to the returned Yahoo consent URL

### Requirement: Handle the OAuth return
Returning to `/connect_league?platform=YAHOO&yahooLinked=1` SHALL show the linked state and resume onboarding for the carried league id; a league that is already onboarded SHALL route the user into their existing league dashboard rather than erroring; a declined/failed link SHALL show an inline retry alert.

#### Scenario: Linked return
- **WHEN** the browser returns to `/connect_league` with `platform=YAHOO&yahooLinked=1` and a `leagueId`
- **THEN** the page shows a "Yahoo account connected" state and resumes onboarding for that league id via `POST /leagues` with `platform=YAHOO`

#### Scenario: Already onboarded league
- **WHEN** the return resumes onboarding and `POST /leagues` responds `200 "League already onboarded"` with a null `data` (the league already exists)
- **THEN** the page skips job polling and routes the user into their existing league dashboard (`/home`) rather than showing a generic error

#### Scenario: Declined or failed
- **WHEN** the return carries `yahooLinked=0`
- **THEN** an inline retry alert ("Yahoo linking was cancelled or failed — try again") is shown with a retry CTA (no global banner, no hard error page)

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

### Requirement: Opt a Yahoo league into automatic refresh

The Yahoo connect flow SHALL present an "enable automatic weekly refresh" checkbox with an
explanatory tooltip, defaulting to off, and SHALL record the owner's choice so the scheduled refresh
honors it. Because Yahoo authorization is already stored, enabling only sets the league's opt-in; no
additional credentials are collected. The tooltip SHALL explain that enabling refreshes the league
weekly during the season using the existing Yahoo authorization.

#### Scenario: Checkbox present with tooltip

- **WHEN** the Yahoo connect flow renders for a league the caller will own
- **THEN** an "enable automatic weekly refresh" checkbox is shown with a tooltip explaining the league
  is refreshed weekly during the season using the stored Yahoo authorization

#### Scenario: Default off (opt-in)

- **WHEN** the Yahoo connect flow renders
- **THEN** the automatic-refresh checkbox defaults to unchecked

#### Scenario: Choice recorded

- **WHEN** the user completes the Yahoo connect flow with the checkbox checked
- **THEN** the league is recorded as opted into automatic refresh
