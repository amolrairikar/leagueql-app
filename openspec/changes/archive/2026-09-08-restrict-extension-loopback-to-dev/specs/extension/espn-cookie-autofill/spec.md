## ADDED Requirements

### Requirement: Production manifest excludes loopback origins
The published extension's `content_scripts.matches` SHALL be limited to LeagueQL production origins and SHALL NOT include `http://localhost/*` or `http://127.0.0.1/*`. Loopback match patterns SHALL be present only in dev builds, added via a build-time flag or a separate dev manifest, so that no page served from the user's loopback interface can trigger the page↔extension cookie channel in the published extension.

#### Scenario: Published manifest
- **WHEN** the extension is built for publishing (production)
- **THEN** its `content_scripts.matches` contains only LeagueQL origins (`https://leagueql.com/*`, `https://*.leagueql.com/*`) and no `localhost` or `127.0.0.1` entries

#### Scenario: Dev build
- **WHEN** the extension is built for local development
- **THEN** loopback match patterns are added via a build-time flag / separate dev manifest, scoped as narrowly as practical to the dev server, and are absent from the published artifact
