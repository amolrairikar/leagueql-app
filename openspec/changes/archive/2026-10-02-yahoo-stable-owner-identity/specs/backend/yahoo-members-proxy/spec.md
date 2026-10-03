# Spec Delta

## MODIFIED Requirements

### Requirement: Return Yahoo league members
The API SHALL return the destination Yahoo league's managers for a caller with a valid linked Yahoo token, falling back to the Yahoo owner id when a nickname is absent. `{leagueId}` is the numeric source league; the destination Yahoo league id is the `yahooLeagueId` query parameter. Each manager's `owner_id` SHALL follow the same per-team rule as onboarding: the real Yahoo `guid` when it is unmasked and unique in the league, otherwise the per-league `manager_id`.

#### Scenario: Valid request
- **WHEN** `POST /leagues/{leagueId}/yahoo_members?yahooLeagueId={id}` is called by the source league owner who has a valid linked Yahoo token and is a member of the destination Yahoo league
- **THEN** the API returns `200` with `data: [{ owner_id, display_name }]`, where `owner_id` is the manager's real Yahoo `guid`, or the per-league `manager_id` when that guid is masked, missing, or duplicated

#### Scenario: Masked guids
- **WHEN** Yahoo masks every manager's guid (e.g. `--hidden--`) in the destination league
- **THEN** each returned `owner_id` is that manager's distinct per-league `manager_id`

#### Scenario: Manager without a nickname
- **WHEN** a returned manager has no `nickname`
- **THEN** its `display_name` falls back to the manager's `owner_id`
