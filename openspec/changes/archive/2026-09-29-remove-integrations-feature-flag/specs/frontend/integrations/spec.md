## ADDED Requirements

### Requirement: Show the Integrations page in the sidebar
The sidebar SHALL always show an "Integrations" item in a "Community" group linking to `/integrations`, and the
`/integrations` route SHALL render the Integrations page.

#### Scenario: Nav item shown
- **WHEN** a signed-in user views the sidebar
- **THEN** a "Community" group with an "Integrations" item linking to `/integrations` is shown

#### Scenario: Route renders the page
- **WHEN** a signed-in user navigates to `/integrations`
- **THEN** the Integrations page renders

## REMOVED Requirements

### Requirement: Gate the Integrations page behind a feature flag
**Reason**: The Integrations feature has launched; the `integrations` flag is retired.
**Migration**: None. Replaced by "Show the Integrations page in the sidebar", which keeps the flag-on behavior
unconditionally.
