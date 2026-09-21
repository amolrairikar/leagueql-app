# Spec Delta

## MODIFIED Requirements

### Requirement: Inline connect routing by existence check
The inline connect form SHALL resolve the league via `getLeague` and route by outcome, surfacing invite-link guidance on an ESPN `403`. For Yahoo, the form SHALL attempt an in-place onboard (`POST /leagues` with `platform=YAHOO`) before any OAuth redirect, so that an already-linked caller never re-visits Yahoo's consent screen; the consent redirect is used only when the caller has no stored Yahoo link.

#### Scenario: Sleeper not onboarded
- **WHEN** the inline form resolves a Sleeper league to `404`
- **THEN** it onboards in place

#### Scenario: ESPN not onboarded
- **WHEN** the inline form resolves an ESPN league to `404`
- **THEN** it routes to `/connect_league` to onboard

#### Scenario: ESPN member gate
- **WHEN** the inline form resolves an ESPN league to `403` (onboarded but caller not a member)
- **THEN** it surfaces an inline message directing the caller to an owner's invite link, without prompting for ESPN cookies

#### Scenario: Yahoo already linked — onboard in place
- **WHEN** a Yahoo league is connected and `POST /leagues` (`platform=YAHOO`) succeeds with a `correlation_id` (the caller has a stored Yahoo link)
- **THEN** the form polls the job to completion in place with the same progress UI as Sleeper and, on success, navigates to `/home` — without redirecting to Yahoo's consent screen

#### Scenario: Yahoo already onboarded
- **WHEN** a Yahoo league is connected and `POST /leagues` responds `200` with a null `data` (the league already exists)
- **THEN** the form skips polling and routes the caller into the existing league dashboard (`/home`), without redirecting to Yahoo's consent screen

#### Scenario: Yahoo not linked — begin consent
- **WHEN** a Yahoo league is connected and `POST /leagues` responds `403` ("Link your Yahoo account first")
- **THEN** the form calls `GET /leagues/yahoo/oauth/authorize?leagueId=<id>` and navigates the browser (full-page redirect) to the returned Yahoo consent URL

#### Scenario: Yahoo link revoked
- **WHEN** a Yahoo onboard job fails with the `YAHOO_AUTH` re-link signal (a stored link whose token was revoked)
- **THEN** the form restarts the Yahoo OAuth step rather than showing a generic failure

#### Scenario: Other failure
- **WHEN** the existence check fails for another reason
- **THEN** a generic inline message is shown
