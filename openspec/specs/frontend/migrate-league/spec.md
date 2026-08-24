# migrate-league Specification

## Purpose
The `/migrate_league` multi-step flow migrates an onboarded league to a new platform while preserving all-time history. It confirms the source league, collects the destination platform + league ID (and ESPN cookies/season if the destination is ESPN), maps each source-platform manager to a destination member, submits to `POST /leagues/{leagueId}/migrate`, and polls until the job completes.

## Requirements

### Requirement: Collect migration inputs and mapping
The flow SHALL confirm the source league, collect the destination platform + league ID, fetch ESPN destination members via the proxy for mapping, and require every source manager to be mapped or marked not returning before submission.

#### Scenario: Build the migration
- **WHEN** the user proceeds through the flow
- **THEN** it confirms the source league, collects the destination platform + league ID, and builds a manager mapping

#### Scenario: ESPN destination members
- **WHEN** the destination is ESPN
- **THEN** its members are fetched via the ESPN members proxy and shown for mapping

#### Scenario: All managers mapped
- **WHEN** the user attempts to submit
- **THEN** submission is blocked until every source manager is mapped or explicitly marked not returning (`__not_returning__`)

### Requirement: Validate ESPN season input live
The ESPN latest-season field SHALL accept any number of digits and surface an inline error live when the value is not exactly a 4-digit year.

#### Scenario: Non-4-digit season
- **WHEN** the user types a season that is not exactly a 4-digit year
- **THEN** an inline error ("Latest season must be a 4-digit number (e.g. 2026)") appears live without blocking input; a missing value shows "Season is required for ESPN"

### Requirement: ESPN credential handling with extension support
ESPN credentials SHALL be transmitted once, cleared after use, never logged, with extension auto-fill offered when detected and manual entry always accepted.

#### Scenario: Extension detection
- **WHEN** the extension is detected
- **THEN** an "Autofill cookies from ESPN" button is shown; when not detected, an inline Chrome Web Store install link is shown, and manual entry is always accepted

### Requirement: Submit and poll to completion
Submitting SHALL call migrate and poll job status to completion, surfacing `409`/failure messages, and land the user in the app with unified cross-platform history on success.

#### Scenario: Successful migration
- **WHEN** the user submits a valid migration
- **THEN** it calls migrate, polls the ~120s job to completion, and on success lands the user in the app with unified cross-platform history

#### Scenario: Conflict
- **WHEN** the backend returns `409` (destination already onboarded or an operation already in progress)
- **THEN** a clear message is surfaced and re-submit is blocked
