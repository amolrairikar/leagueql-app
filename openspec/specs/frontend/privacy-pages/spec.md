# privacy-pages Specification

## Purpose
Public privacy policy pages: a general app privacy page (`/privacy`) and a dedicated privacy page for the Chrome extension (`/extension-privacy`). The extension privacy page is required for the Chrome Web Store listing and explains how ESPN cookies are handled.

## Requirements

### Requirement: Render public privacy pages
`/privacy` and `/extension-privacy` SHALL render publicly (accessible without auth).

#### Scenario: Pages render publicly
- **WHEN** an unauthenticated visitor opens `/privacy` or `/extension-privacy`
- **THEN** the general and extension-specific privacy policies render respectively

### Requirement: Accurately disclose ESPN cookie handling
The extension privacy page SHALL accurately state that ESPN cookies are read only for onboarding, transmitted once over HTTPS, and never stored/logged, staying consistent with actual behavior.

#### Scenario: Cookie disclosure
- **WHEN** the extension privacy page renders
- **THEN** it describes ESPN cookie handling accurately (read only for onboarding, transmitted once over HTTPS, never stored/logged), consistent with the app and extension's real data handling

### Requirement: Disclose Yahoo OAuth token storage
The general privacy page (`/privacy`) SHALL disclose Yahoo as a supported data source and SHALL state that, unlike ESPN cookies (which are never stored), LeagueQL persists Yahoo OAuth access/refresh tokens encrypted at rest so it can refresh league data, that these tokens are never sold or shared, and that they are removed when the user requests deletion.

#### Scenario: Yahoo token disclosure
- **WHEN** the general privacy page renders
- **THEN** it lists Yahoo among the fantasy platforms LeagueQL analyzes and states that Yahoo OAuth tokens are stored encrypted at rest (to refresh league data), never sold or shared, and removed on request (without exposing internal encryption implementation details)
