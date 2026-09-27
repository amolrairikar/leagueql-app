# Spec Delta

## MODIFIED Requirements

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
