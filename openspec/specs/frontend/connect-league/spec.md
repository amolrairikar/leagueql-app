# connect-league Specification

## Purpose
The `/connect_league` flow lets a signed-in user onboard a new league or refresh an existing one. The user selects a platform, enters a league ID (and latest season + ESPN cookies for private ESPN leagues), submits to `POST /leagues`, and polls `GET /jobs/{jobId}` until the job completes or fails. The flow is ownership/membership aware: a non-member of a private league (ESPN or Yahoo) is directed to an owner's invite link rather than onboarding.

## Requirements

### Requirement: Onboard a league
A user SHALL be able to onboard a public Sleeper or ESPN league with platform + league ID (+ season for ESPN), with pre-filled platform/league-ID fields locked.

#### Scenario: Onboard a public league
- **WHEN** a user submits a valid platform and league ID (plus season for ESPN)
- **THEN** the league is onboarded via `POST /leagues`

#### Scenario: Pre-filled fields locked
- **WHEN** the user arrives with a known platform + league ID
- **THEN** those fields are locked against edits

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

### Requirement: Validate season input live
The ESPN latest-season field SHALL accept any number of digits and surface an inline validation error live as the user types when the value is not exactly a 4-digit year.

#### Scenario: Non-4-digit season
- **WHEN** the user types a value that is not exactly a 4-digit year
- **THEN** an inline error ("Latest season must be a 4-digit number (e.g. 2026)") appears live without blocking further input; a missing value shows "Latest season is required"

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

The ESPN connect/refresh form SHALL present an "enable automatic weekly refresh" checkbox with an
explanatory tooltip, defaulting to off for a new onboard and prefilled from the league's current
enrollment when refreshing an existing league. When checked, the form SHALL send the opt-in with the
`POST /leagues` submit so the owner's cookies are stored for reuse; when unchecked, it SHALL send the
opt-out. The tooltip SHALL explain that enabling stores the ESPN cookies encrypted to refresh the
league weekly during the season and that cookies can expire, occasionally requiring re-entry.

#### Scenario: Checkbox present with tooltip

- **WHEN** the ESPN connect/refresh form renders
- **THEN** an "enable automatic weekly refresh" checkbox is shown with a tooltip explaining that the
  ESPN cookies are stored encrypted, the league is refreshed weekly during the season, and cookies
  can expire and occasionally need re-entering

#### Scenario: Default off for a new onboard

- **WHEN** a user onboards a new ESPN league
- **THEN** the automatic-refresh checkbox defaults to unchecked (opt-in)

#### Scenario: Prefilled from current enrollment on refresh

- **WHEN** the form opens for an existing ESPN league the caller owns
- **THEN** the checkbox reflects that league's current `auto_refresh_enabled` state

#### Scenario: Choice sent with submit

- **WHEN** the user submits the ESPN form
- **THEN** the automatic-refresh opt-in choice is included in the `POST /leagues` request body
