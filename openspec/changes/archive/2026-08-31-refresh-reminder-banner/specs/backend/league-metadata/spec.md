## MODIFIED Requirements

### Requirement: Return league metadata
The API SHALL return the onboarded seasons and league name with `200` for an onboarded league, and `404` for an un-onboarded one. The `200` payload SHALL additionally include `onboarded_at` (ISO 8601) and `last_refresh_at` (ISO 8601, nullable — absent until the league's first successful refresh), so the frontend can determine when the league's data was last updated.

#### Scenario: Onboarded league
- **WHEN** `GET /leagues/{leagueId}` is called for an onboarded league
- **THEN** the API returns `200` with `{ seasons, league_name, is_owner, last_refresh_at, onboarded_at }`

#### Scenario: Never-refreshed league
- **WHEN** an onboarded league has never been refreshed (no `last_refresh_at` on `METADATA`)
- **THEN** the API returns `200` with `last_refresh_at` null and `onboarded_at` set

#### Scenario: Un-onboarded league
- **WHEN** the league is not in `LEAGUE_LOOKUP`
- **THEN** the API returns `404` with an onboarding hint

#### Scenario: Missing league name tolerated
- **WHEN** an older `METADATA` item has no `league_name`
- **THEN** the field may be null/omitted and the frontend tolerates it
