# connect-league Specification

## Purpose
The connect/refresh flow lets a signed-in user onboard a new league or refresh an existing one. The user selects a platform and enters a league ID (and, for private ESPN leagues, the owner's ESPN cookies — the season is derived automatically, never entered), submits to `POST /leagues`, and polls `GET /jobs/{jobId}` until the job completes or fails. ESPN onboarding of a not-yet-onboarded league begins inline on the landing page and refreshing an existing ESPN league happens through an in-dashboard dialog, while `/connect_league` still handles the Yahoo OAuth return. The flow is ownership/membership aware: a non-member of a private league (ESPN or Yahoo) is directed to an owner's invite link rather than onboarding.

## Requirements

### Requirement: Onboard a league
A user SHALL be able to onboard a public Sleeper or ESPN league with platform + league ID. For ESPN, the season is derived automatically (see "Derive the ESPN season automatically") rather than entered by the user. ESPN onboarding of a not-yet-onboarded league begins inline on the landing page (frontend/landing-page), and refreshing an existing ESPN league happens through the in-dashboard Refresh League dialog (frontend/navigation-sidebar); both derive the season automatically. There is no standalone ESPN/Sleeper onboard/refresh form.

#### Scenario: Onboard a public league
- **WHEN** a user submits a valid platform and league ID
- **THEN** the league is onboarded via `POST /leagues`, with the ESPN `season` supplied automatically

#### Scenario: Pre-filled fields locked
- **WHEN** the Refresh League dialog opens for the currently-viewed league
- **THEN** it is scoped to that league — there are no editable platform/league-ID fields to change

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

### Requirement: Private ESPN credentials handling

Private ESPN onboarding SHALL accept `s2`/`swid` via extension auto-fill or manual entry, transmit
them once over HTTPS, clear them from the browser on success, and never log them or keep them in
browser storage. The backend persists them (encrypted at rest) only when the user opts into
automatic refresh (backend/espn-credential-storage); without opt-in they are used only for the
request and not stored.

#### Scenario: Cookies via extension or manual

- **WHEN** a private ESPN league is onboarded
- **THEN** cookies can be auto-filled by the extension or entered manually, and are cleared
  (`clearEspnCookies`) on success

#### Scenario: Extension detection

- **WHEN** the extension is detected
- **THEN** an "Autofill cookies from ESPN" button is shown; when not detected, an inline Chrome Web
  Store install link is shown instead

#### Scenario: Credentials never persisted

- **WHEN** ESPN cookies are submitted
- **THEN** they appear in no logs and are not kept in browser storage; on the server they are stored
  (encrypted at rest) only when the user enabled automatic refresh, and are otherwise not persisted

### Requirement: Poll job status
The UI SHALL poll job status long enough to capture completion of slow (~120s) jobs and show in-progress, success, and failure states with the backend failure message.

#### Scenario: Job lifecycle shown
- **WHEN** an onboard/refresh job runs
- **THEN** the UI shows in-progress, then success or failure, surfacing the backend `failure_reason` and allowing retry

#### Scenario: Slow job captured
- **WHEN** a job takes up to ~120s
- **THEN** polling persists long enough to observe `COMPLETED` rather than falsely timing out

### Requirement: Ownership/membership-aware routing
The initial `getLeague` check SHALL route by outcome so a non-owner is not sent through an owner-only refresh, and a non-member of a gated league (ESPN or Yahoo) is directed to obtain an invite link rather than being asked for platform credentials.

#### Scenario: Non-owner of an existing league
- **WHEN** the league exists (`200`) and the caller is not its owner
- **THEN** the flow opens the dashboard without sending an owner-only refresh

#### Scenario: ESPN non-member join
- **WHEN** the lookup returns `403` for an ESPN league
- **THEN** the flow does not attempt cookie-based membership verification; it surfaces a message that the league is private and the caller needs an invite link from the league owner to join

#### Scenario: Yahoo non-member join
- **WHEN** the lookup returns `403` for a Yahoo league
- **THEN** the flow surfaces the same private-league invite-link guidance and does not ask for platform credentials

### Requirement: Surface errors inline and refresh cache on success
A non-404 lookup failure or an exhausted submit failure SHALL be surfaced inline (no global banner), and a successful onboard/refresh SHALL clear the API cache before routing into the app. A `429` refresh cooldown response, and a `409` already-up-to-date / in-progress response, SHALL be surfaced as a benign notice using the backend `detail` message — a neutral title without a contact-support prompt — rather than a generic failure.

#### Scenario: Lookup/submit failure
- **WHEN** the initial `getLeague` fails for a non-404 reason, or the `POST /leagues` submit fails (network/5xx after retries)
- **THEN** the failure is surfaced in the form's failed-state alert rather than aborting silently

#### Scenario: Refresh cooldown surfaced as benign notice
- **WHEN** the `POST /leagues` refresh submit returns `429` (weekly cooldown) or `409` (already up to date / in progress)
- **THEN** the backend `detail` message is shown in the form as a benign notice with a neutral title and no contact-support prompt, and the user is not routed to home

#### Scenario: Cache cleared on success
- **WHEN** an onboard/refresh succeeds
- **THEN** the in-memory API cache is cleared (`clearApiCache`) and the user is routed to home reflecting the fresh data

#### Scenario: Demo mode
- **WHEN** the app is in demo mode
- **THEN** connecting is disabled/redirected

### Requirement: Opt an ESPN league into automatic refresh

The ESPN landing-page onboard and the in-dashboard Refresh League dialog SHALL each present an "enable automatic weekly refresh" checkbox with an explanatory tooltip, defaulting to off. When checked, the opt-in SHALL be sent with the `POST /leagues` submit so the owner's cookies are stored for reuse; when unchecked, the opt-out SHALL be sent. The tooltip SHALL explain that enabling stores the ESPN cookies encrypted to refresh the league weekly during the season and that cookies can expire, occasionally requiring re-entry.

#### Scenario: Checkbox present with tooltip

- **WHEN** the ESPN landing-page onboard or the Refresh League dialog renders
- **THEN** an "enable automatic weekly refresh" checkbox is shown with a tooltip explaining that the
  ESPN cookies are stored encrypted, the league is refreshed weekly during the season, and cookies
  can expire and occasionally need re-entering

#### Scenario: Default off for a new onboard

- **WHEN** a user onboards a new ESPN league on the landing page
- **THEN** the automatic-refresh checkbox defaults to unchecked (opt-in)

#### Scenario: Prefilled from current enrollment on refresh

- **WHEN** the Refresh League dialog opens for an existing ESPN league the caller owns
- **THEN** the checkbox reflects that league's current `auto_refresh_enabled` state — which, because the dialog is only shown for a not-enrolled league, defaults to unchecked

#### Scenario: Choice sent with submit

- **WHEN** the user submits the ESPN landing-page onboard or the Refresh League dialog
- **THEN** the automatic-refresh opt-in choice is included in the `POST /leagues` request body
