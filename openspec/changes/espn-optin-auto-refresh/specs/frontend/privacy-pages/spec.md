## MODIFIED Requirements

### Requirement: Accurately disclose ESPN cookie handling

The extension privacy page SHALL accurately state that ESPN cookies are read only for onboarding and
refresh, transmitted once over HTTPS, and never stored or logged by the extension itself, and SHALL
state that once the cookies reach LeagueQL they are stored on LeagueQL's servers only when the user
enables automatic refresh (encrypted at rest) and are otherwise not retained — staying consistent
with actual behavior.

#### Scenario: Cookie disclosure

- **WHEN** the extension privacy page renders
- **THEN** it describes ESPN cookie handling accurately: the extension reads them only for
  onboarding/refresh, transmits them once over HTTPS, and never stores or logs them; and on
  LeagueQL's servers they are retained only when the user enables automatic refresh (stored encrypted
  at rest) and are otherwise not stored — consistent with the app and extension's real data handling

### Requirement: Disclose Yahoo OAuth token storage

The general privacy page (`/privacy`) SHALL disclose Yahoo as a supported data source and SHALL state
that LeagueQL persists Yahoo OAuth access/refresh tokens encrypted at rest so it can refresh league
data, that these tokens are never sold or shared, and that they are removed when the user requests
deletion.

#### Scenario: Yahoo token disclosure

- **WHEN** the general privacy page renders
- **THEN** it lists Yahoo among the fantasy platforms LeagueQL analyzes and states that Yahoo OAuth
  tokens are stored encrypted at rest (to refresh league data), never sold or shared, and removed on
  request (without exposing internal encryption implementation details)

## ADDED Requirements

### Requirement: Disclose ESPN cookie storage when auto-refresh is enabled

The general privacy page (`/privacy`) SHALL state that ESPN cookies are stored (encrypted at rest)
only when the user enables automatic refresh for an ESPN league, are used solely to refresh that
user's league data, are never sold or shared, and are removed once the user turns automatic refresh
off or deletes their last ESPN league — and that ESPN cookies are not stored otherwise.

#### Scenario: ESPN storage disclosure

- **WHEN** the general privacy page renders
- **THEN** it states that ESPN cookies are stored encrypted at rest only when the user enables
  automatic refresh, used only to refresh league data, never sold or shared, removed when auto-refresh
  is turned off or the last ESPN league is removed, and not stored otherwise (without exposing
  internal encryption implementation details)
