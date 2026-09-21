## ADDED Requirements

### Requirement: Onboard a Yahoo league
The API SHALL accept an `ONBOARD` request for a Yahoo league only when the requesting Clerk user
has a valid linked Yahoo account, and SHALL then create a `JOB_STATUS` item, invoke the onboarder
Lambda (carrying the owner's Clerk user id, no ESPN cookies), and return `201`. An unlinked caller
SHALL be told to link first rather than starting a job.

#### Scenario: Linked Yahoo onboard
- **WHEN** `POST /leagues?requestType=ONBOARD` with `platform=YAHOO` is called by a user with a
  valid Yahoo link for a not-yet-onboarded league
- **THEN** the API returns `201` with `{ detail, data: { correlation_id } }` and invokes the
  onboarder Lambda with the owner's Clerk user id and no `s2`/`swid`

#### Scenario: Unlinked Yahoo onboard
- **WHEN** a Yahoo `ONBOARD`/`REFRESH` is requested by a user with no valid Yahoo link
- **THEN** the API returns `403` with a "link your Yahoo account first" signal the frontend routes
  to the OAuth step, and no job is created

#### Scenario: Already onboarded Yahoo league
- **WHEN** a Yahoo `ONBOARD` is issued for a league id already present in `LEAGUE_LOOKUP`
- **THEN** the API returns `200` "League already onboarded" and does not re-run the pipeline

### Requirement: Obtain and refresh Yahoo credentials in the onboarder
The onboarder SHALL obtain a valid Yahoo access token for the onboarding owner's linked account
and refresh it as needed for the duration of a run (which can exceed the access token's lifetime),
and SHALL never write Yahoo access/refresh tokens to logs, DynamoDB view items, or S3 raw payloads.
When the owner's Yahoo link is missing or its refresh token has been revoked, onboarding SHALL fail
with a `YAHOO_AUTH` re-link signal rather than a generic failure.

#### Scenario: Token refreshed mid-run
- **WHEN** the onboarder's Yahoo access token nears or reaches expiry during a multi-season fetch
- **THEN** it is transparently refreshed and the run continues without failing

#### Scenario: Revoked Yahoo link
- **WHEN** the onboarding owner's Yahoo refresh token has been revoked
- **THEN** the `JOB_STATUS` item is set to `FAILED` with a `YAHOO_AUTH` code the frontend surfaces
  as a reconnect prompt

#### Scenario: Tokens never persisted
- **WHEN** a Yahoo league is onboarded
- **THEN** no Yahoo access or refresh token value appears in any log line, DynamoDB item, or S3
  object

### Requirement: Resolve the Yahoo league and its season history
Because Yahoo addresses a league by a season-specific `league_key` and issues a new numeric league
id each season, the onboarder SHALL resolve the entered numeric league id to the owner's Yahoo
`league_key` (verifying the owner belongs to that league) and SHALL walk the per-season `renew`
chain to onboard the full history under a single canonical league, mirroring the ESPN/Sleeper
whole-history behavior. A `REFRESH` SHALL fetch only the current season.

#### Scenario: Full history via the renew chain
- **WHEN** a Yahoo league with prior renewed seasons is onboarded
- **THEN** every season in the `renew` lineage is fetched and processed under one canonical league
  id, and `LEAGUE_COUNT` is incremented once

#### Scenario: League not owned by the caller
- **WHEN** the entered league id is not among the linked user's Yahoo leagues
- **THEN** onboarding fails with a not-found/authorization outcome rather than fetching another
  user's league

#### Scenario: Yahoo refresh fetches the current season only
- **WHEN** a Yahoo league is refreshed
- **THEN** only the current season's `league_key` is fetched and reprocessed

### Requirement: Parse Yahoo team, manager, and logo identities
The onboarder SHALL parse each team's identity, primary manager (owner id + display name), and
logo from the Yahoo `/teams` payload. Because Yahoo returns a collection either as a numeric-keyed
object (`{"0": {...}, "count": N}`, used for large collections like teams and roster players) or as
a plain list (`[{...}]`, used for small nested sub-collections like `managers` and `team_logos`),
the parsing SHALL handle both shapes so owner ids, display names, and logos populate. Each team's
primary-owner id SHALL be unique within the league: the manager `guid` SHALL be used when it is
present for every team and distinct across the league; otherwise the per-league `manager_id` SHALL
be used, so leagues where Yahoo masks the guid do not collapse every team onto one manager.

#### Scenario: Managers and logos parsed from list-shaped sub-collections
- **WHEN** a Yahoo `/teams` response returns each team's `managers` and `team_logos` as plain lists
- **THEN** each team's primary owner id, display name, and logo URL are populated (not null),
  and the derived member rows carry those owner ids

#### Scenario: Managers parsed from a numeric-keyed sub-collection
- **WHEN** a Yahoo sub-collection is instead returned as a numeric-keyed object
- **THEN** the same fields are parsed identically

#### Scenario: Masked or duplicate guids fall back to manager_id
- **WHEN** Yahoo returns the same (masked) manager `guid` for every team, or omits it
- **THEN** each team's primary-owner id comes from its distinct per-league `manager_id`, so every
  team keeps a distinct owner and the correct manager name rather than collapsing onto the first

#### Scenario: Distinct guids preserved for cross-season continuity
- **WHEN** Yahoo exposes a distinct guid for every team (e.g. a private league)
- **THEN** those guids are used as the owner ids so the same manager stays continuous across
  seasons
