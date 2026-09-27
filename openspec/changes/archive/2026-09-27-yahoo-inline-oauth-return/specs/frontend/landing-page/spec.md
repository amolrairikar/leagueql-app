# Spec Delta

## ADDED Requirements

### Requirement: Resume the Yahoo OAuth return inline
On load, `/` SHALL detect the Yahoo OAuth return params (`platform=YAHOO`, `yahooLinked`, and an optional `leagueId`) and resolve the return inline in the connect form, without routing to a separate page. On `yahooLinked=1` with a `leagueId` it SHALL open the connect form with Yahoo selected and resume onboarding for that league id with the same hero progress UI (polling the job, applying the auto-refresh opt-in chosen before the redirect, and navigating to `/home` on success). On `yahooLinked=0` it SHALL open the connect form with Yahoo selected and show an inline retry alert instead of onboarding. The return params SHALL be consumed so a reload does not re-trigger onboarding, and a revoked/expired link surfaced during the resume SHALL restart the Yahoo OAuth step rather than showing a generic failure.

#### Scenario: Linked return resumes onboarding inline
- **WHEN** `/` loads with `platform=YAHOO&yahooLinked=1&leagueId=<id>` and the visitor is signed in
- **THEN** the connect form opens with Yahoo selected and onboarding resumes inline (`POST /leagues` with `platform=YAHOO`, polling with the hero progress bar), navigating to `/home` on success

#### Scenario: Linked return for an already-onboarded league
- **WHEN** the inline resume calls `POST /leagues` and it responds `200` with a null `data` (the league already exists)
- **THEN** polling is skipped and the visitor is routed into the existing league dashboard (`/home`)

#### Scenario: Auto-refresh opt-in applied on return
- **WHEN** the visitor opted a Yahoo league into automatic refresh before the consent redirect and then returns with `yahooLinked=1`
- **THEN** the inline resume sends that opt-in with `POST /leagues`

#### Scenario: Declined return
- **WHEN** `/` loads with `platform=YAHOO&yahooLinked=0`
- **THEN** the connect form opens with Yahoo selected and an inline retry alert ("Yahoo linking was cancelled or failed — try again") is shown, and no onboard request is sent

#### Scenario: Revoked link on return
- **WHEN** the inline resume fails with the `YAHOO_AUTH` re-link signal (or a `403` "link first")
- **THEN** the Yahoo OAuth step is restarted rather than a generic failure being shown

#### Scenario: Return params not re-triggered on reload
- **WHEN** the Yahoo return has been handled and the page is reloaded
- **THEN** the consumed `platform`/`yahooLinked`/`leagueId` params no longer re-trigger onboarding
