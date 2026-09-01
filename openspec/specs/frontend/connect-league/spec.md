# connect-league Specification

## Purpose
The `/connect_league` flow lets a signed-in user onboard a new league or refresh an existing one. The user selects a platform, enters a league ID (and latest season + ESPN cookies for private ESPN leagues), submits to `POST /leagues`, and polls `GET /jobs/{jobId}` until the job completes or fails. The flow is ownership/membership aware: joining (ESPN membership verification) is a distinct UI from onboarding.

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
Private ESPN onboarding SHALL accept `s2`/`swid` via extension auto-fill or manual entry, transmit them once over HTTPS, clear them on success, and never persist or log them.

#### Scenario: Cookies via extension or manual
- **WHEN** a private ESPN league is onboarded
- **THEN** cookies can be auto-filled by the extension or entered manually, and are cleared (`clearEspnCookies`) on success

#### Scenario: Extension detection
- **WHEN** the extension is detected
- **THEN** an "Autofill cookies from ESPN" button is shown; when not detected, an inline Chrome Web Store install link is shown instead

#### Scenario: Credentials never persisted
- **WHEN** ESPN cookies are submitted
- **THEN** they appear in no logs or persistent storage

### Requirement: Poll job status
The UI SHALL poll job status long enough to capture completion of slow (~120s) jobs and show in-progress, success, and failure states with the backend failure message.

#### Scenario: Job lifecycle shown
- **WHEN** an onboard/refresh job runs
- **THEN** the UI shows in-progress, then success or failure, surfacing the backend `failure_reason` and allowing retry

#### Scenario: Slow job captured
- **WHEN** a job takes up to ~120s
- **THEN** polling persists long enough to observe `COMPLETED` rather than falsely timing out

### Requirement: Ownership/membership-aware routing
The initial `getLeague` check SHALL route by outcome so a non-owner is not sent through an owner-only refresh, and an ESPN non-member verifies membership first.

#### Scenario: Non-owner of an existing league
- **WHEN** the league exists (`200`) and the caller is not its owner
- **THEN** the flow opens the dashboard without sending an owner-only refresh

#### Scenario: ESPN non-member join
- **WHEN** the lookup returns `403` for an ESPN league
- **THEN** the flow verifies membership via `verify-membership` (Join League dialog from the landing form, or inline with already-entered cookies on the connect page) before opening the dashboard, surfacing ESPN-rejected cookies inline

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
