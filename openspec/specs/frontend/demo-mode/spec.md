# demo-mode Specification

## Purpose
Let visitors explore the full app with sample data, without signing in or connecting a real league. When demo mode is active, protected routes are accessible without authentication, API calls are served from local demo fixtures, and a persistent banner reminds the user they are viewing sample data.

## Requirements

### Requirement: Render the app from demo fixtures
With demo mode active, all analytics pages SHALL render using demo fixtures without sign-in and without live API calls, including the Sleeper-only Transactions page.

#### Scenario: Analytics from fixtures
- **WHEN** demo mode is active
- **THEN** all analytics pages render from demo fixtures without requiring sign-in and without making live API calls

#### Scenario: Transactions in demo
- **WHEN** the Transactions page renders in demo mode
- **THEN** it shows sample transactions from the demo dataset's `TRANSACTIONS#2025` bucket

### Requirement: Show the demo banner
The demo banner SHALL be shown on every in-app page while demo mode is active.

#### Scenario: Banner present
- **WHEN** any in-app page renders in demo mode
- **THEN** the demo banner is shown

### Requirement: No live mutations in demo mode
No live backend mutations SHALL occur from within demo mode.

#### Scenario: Mutations disabled
- **WHEN** a connect/refresh/migrate action is attempted in demo mode
- **THEN** it is disabled or redirected, causing no real backend mutation

### Requirement: Clear demo state on return to landing
Returning to the landing page by any path while demo mode is active SHALL clear demo state so a league connected afterward is treated as live.

#### Scenario: Exit via landing
- **WHEN** the user reaches the landing page (header link, back button, or direct visit) while demo mode is active
- **THEN** the 24h `demo_mode` cookie/state is cleared, so a subsequently connected league is not served fixtures or bypassing auth
