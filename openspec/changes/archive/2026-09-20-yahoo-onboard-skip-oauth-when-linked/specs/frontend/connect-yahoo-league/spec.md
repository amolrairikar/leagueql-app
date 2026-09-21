# Spec Delta

## MODIFIED Requirements

### Requirement: Start the OAuth link on Connect
Clicking Connect with Yahoo selected SHALL first attempt an in-place onboard (`POST /leagues` with `platform=YAHOO`) for the entered league id, and SHALL redirect the browser to Yahoo's consent screen only when the caller has no stored Yahoo link. An already-linked caller onboards in place (no consent redirect); a `403` "link first" response triggers the OAuth redirect via `GET /leagues/yahoo/oauth/authorize`.

#### Scenario: Already linked — no consent redirect
- **WHEN** the user selects Yahoo, enters a league id, and clicks Connect while already linked (the onboard call returns a `correlation_id` or a `200` null-`data` "already onboarded")
- **THEN** the league is onboarded in place and the browser is NOT redirected to Yahoo's consent screen

#### Scenario: Begin consent
- **WHEN** the user selects Yahoo, enters a league id, and clicks Connect while not linked (the onboard call returns `403` "Link your Yahoo account first")
- **THEN** the form calls `GET /leagues/yahoo/oauth/authorize?leagueId=<id>` and navigates the browser (full-page redirect) to the returned Yahoo consent URL
