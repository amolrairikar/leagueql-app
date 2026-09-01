## MODIFIED Requirements

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
