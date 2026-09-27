## MODIFIED Requirements

### Requirement: Inline connect routing by existence check
The inline connect form SHALL resolve the league via `getLeague` and route by outcome. ESPN credential inputs (SWID and espn_s2, each with a per-field tooltip explaining how to retrieve the cookie, plus the Chrome-extension autofill helper or install promo below the inputs) and the "enable automatic weekly refresh" opt-in checkbox SHALL NOT be shown merely because ESPN is selected; they SHALL be revealed only after a Connect submit whose existence check returns `404` (not onboarded). When these fields are revealed, an explanatory message "League not added to LeagueQL yet. Enter your ESPN cookies below to connect." SHALL be shown above them. The first `404` SHALL reveal these fields and send no `POST /leagues` onboard request; a subsequent Connect with SWID/espn_s2 provided SHALL onboard the not-yet-onboarded ESPN league in place — the same way Sleeper onboards in place — rather than routing to `/connect_league`. An ESPN `403` (onboarded, caller not a member) SHALL surface invite-link guidance, and a `200` (caller is a member/owner) SHALL route into the existing dashboard. For Yahoo, the form SHALL attempt an in-place onboard (`POST /leagues` with `platform=YAHOO`) before any OAuth redirect, so that an already-linked caller never re-visits Yahoo's consent screen; the consent redirect is used only when the caller has no stored Yahoo link.

#### Scenario: Sleeper not onboarded
- **WHEN** the inline form resolves a Sleeper league to `404`
- **THEN** it onboards in place

#### Scenario: ESPN credentials hidden until lookup
- **WHEN** ESPN is selected in the inline connect form and no Connect submit has resolved to `404` yet
- **THEN** no SWID or espn_s2 inputs, cookie helper, or ESPN auto-refresh checkbox are shown, and the "League not added to LeagueQL yet" message is not shown

#### Scenario: ESPN credentials entered inline
- **WHEN** a Connect submit resolves an ESPN league to `404` for the first time
- **THEN** the message "League not added to LeagueQL yet. Enter your ESPN cookies below to connect." is shown above the SWID and espn_s2 inputs, which are revealed (each with a per-field tooltip and the extension "Autofill cookies from ESPN" button when the extension is detected, an install promo otherwise, below the inputs) together with the ESPN auto-refresh opt-in checkbox, and no `POST /leagues` onboard request is sent

#### Scenario: ESPN not onboarded
- **WHEN** the credential fields have been revealed, SWID/espn_s2 have been provided, and Connect is submitted again for a league that still resolves to `404`
- **THEN** it onboards the ESPN league in place via `POST /leagues` (polling the job to completion with the same progress UI as Sleeper) and, on success, clears the ESPN cookies from the browser and navigates to `/home` — without routing to `/connect_league`

#### Scenario: ESPN onboard without credentials
- **WHEN** the credential fields are revealed but the user submits Connect with SWID and espn_s2 still empty
- **THEN** an inline error is shown and no `POST /leagues` onboard request is sent

#### Scenario: ESPN season derived automatically
- **WHEN** an ESPN league is onboarded in place
- **THEN** the `season` sent with `POST /leagues` is derived automatically (from the Sleeper NFL-state endpoint, falling back to a clock-derived current fantasy season) and the user is never asked to enter it

#### Scenario: ESPN already onboarded — member routes in
- **WHEN** the inline form resolves an ESPN league to `200` (onboarded and the caller is a member or owner)
- **THEN** it routes into the existing league dashboard (`/home`) without revealing the credential fields

#### Scenario: ESPN member gate
- **WHEN** the inline form resolves an ESPN league to `403` (onboarded but caller not a member)
- **THEN** it surfaces the message "League already onboarded. Please reach out to your leaguemate who onboarded the league to get your league-specific invite link.", without revealing or prompting for ESPN cookies

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
