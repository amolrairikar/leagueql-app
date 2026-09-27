# Spec Delta

## MODIFIED Requirements

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
