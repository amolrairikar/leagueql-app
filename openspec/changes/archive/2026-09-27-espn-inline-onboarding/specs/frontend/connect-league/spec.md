## MODIFIED Requirements

### Requirement: Onboard a league
A user SHALL be able to onboard a public Sleeper or ESPN league with platform + league ID, with pre-filled platform/league-ID fields locked. For ESPN, the season is derived automatically (see "Derive the ESPN season automatically") rather than entered by the user. ESPN onboarding of a not-yet-onboarded league begins inline on the landing page (frontend/landing-page), and refreshing an existing ESPN league happens through the in-dashboard Refresh League dialog (frontend/navigation-sidebar); both derive the season automatically.

#### Scenario: Onboard a public league
- **WHEN** a user submits a valid platform and league ID
- **THEN** the league is onboarded via `POST /leagues`, with the ESPN `season` supplied automatically

#### Scenario: Pre-filled fields locked
- **WHEN** the user arrives with a known platform + league ID
- **THEN** those fields are locked against edits

## ADDED Requirements

### Requirement: Derive the ESPN season automatically
The ESPN `season` sent with `POST /leagues` SHALL be derived automatically rather than entered by the user: the flow SHALL fetch the current NFL season from the Sleeper NFL-state endpoint (`https://api.sleeper.app/v1/state/nfl`) and fall back to a clock-derived current fantasy season when that fetch fails. There SHALL be no user-facing season input in the connect/refresh flow.

#### Scenario: Season fetched from Sleeper
- **WHEN** an ESPN onboard/refresh is submitted and the Sleeper NFL-state endpoint responds
- **THEN** the `season` sent with `POST /leagues` is the `season` value from that response

#### Scenario: Season fetch falls back to the clock
- **WHEN** an ESPN onboard/refresh is submitted and the Sleeper NFL-state fetch fails (non-OK, network error, or unparseable body)
- **THEN** the `season` sent with `POST /leagues` is the clock-derived current fantasy season and the submit is not blocked

#### Scenario: No season input shown
- **WHEN** the ESPN connect/refresh form renders
- **THEN** no "Latest Season" input is shown

## REMOVED Requirements

### Requirement: Validate season input live
**Reason**: The manual ESPN "Latest Season" input has been removed; the season is now derived automatically (see "Derive the ESPN season automatically"), so there is no user-entered season value to validate.
**Migration**: None. Users no longer enter a season; the current NFL season is fetched automatically (with a clock-based fallback) and sent with `POST /leagues`.
