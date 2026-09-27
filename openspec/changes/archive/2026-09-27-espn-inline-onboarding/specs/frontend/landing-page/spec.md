## MODIFIED Requirements

### Requirement: Inline connect routing by existence check
The inline connect form SHALL resolve the league via `getLeague` and route by outcome, surfacing invite-link guidance on an ESPN `403`. When ESPN is selected, the form SHALL show SWID and espn_s2 credential inputs (each with a per-field tooltip explaining how to retrieve the cookie, plus the Chrome-extension autofill helper or install promo below the inputs) and an "enable automatic weekly refresh" opt-in checkbox, and it SHALL onboard a not-yet-onboarded ESPN league (`404`) in place — the same way Sleeper onboards in place — rather than routing to `/connect_league`. For Yahoo, the form SHALL attempt an in-place onboard (`POST /leagues` with `platform=YAHOO`) before any OAuth redirect, so that an already-linked caller never re-visits Yahoo's consent screen; the consent redirect is used only when the caller has no stored Yahoo link.

#### Scenario: Sleeper not onboarded
- **WHEN** the inline form resolves a Sleeper league to `404`
- **THEN** it onboards in place

#### Scenario: ESPN not onboarded
- **WHEN** the inline form resolves an ESPN league to `404` and SWID/espn_s2 have been provided
- **THEN** it onboards the ESPN league in place via `POST /leagues` (polling the job to completion with the same progress UI as Sleeper) and, on success, clears the ESPN cookies from the browser and navigates to `/home` — without routing to `/connect_league`

#### Scenario: ESPN credentials entered inline
- **WHEN** ESPN is selected in the inline connect form
- **THEN** SWID and espn_s2 inputs are shown next to the League ID box, each with a per-field tooltip explaining how to retrieve the cookie, and the extension "Autofill cookies from ESPN" button when the extension is detected (an install promo otherwise) below the inputs; the standalone manual-instructions text block is not shown

#### Scenario: ESPN onboard without credentials
- **WHEN** the user attempts to connect a not-yet-onboarded (`404`) ESPN league without providing SWID and espn_s2
- **THEN** an inline error is shown and no `POST /leagues` onboard request is sent

#### Scenario: ESPN season derived automatically
- **WHEN** an ESPN league is onboarded in place
- **THEN** the `season` sent with `POST /leagues` is derived automatically (from the Sleeper NFL-state endpoint, falling back to a clock-derived current fantasy season) and the user is never asked to enter it

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
