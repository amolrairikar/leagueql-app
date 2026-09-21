# Spec Delta

## ADDED Requirements

### Requirement: Disclose Yahoo OAuth token storage
The general privacy page (`/privacy`) SHALL disclose Yahoo as a supported data source and SHALL state that, unlike ESPN cookies (which are never stored), LeagueQL persists Yahoo OAuth access/refresh tokens encrypted at rest so it can refresh league data, that these tokens are never sold or shared, and that they are removed when the user requests deletion.

#### Scenario: Yahoo token disclosure
- **WHEN** the general privacy page renders
- **THEN** it lists Yahoo among the fantasy platforms LeagueQL analyzes and states that Yahoo OAuth tokens are stored encrypted at rest (to refresh league data), never sold or shared, and removed on request (without exposing internal encryption implementation details)
