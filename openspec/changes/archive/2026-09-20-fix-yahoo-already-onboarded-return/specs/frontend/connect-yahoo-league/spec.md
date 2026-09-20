## MODIFIED Requirements

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
