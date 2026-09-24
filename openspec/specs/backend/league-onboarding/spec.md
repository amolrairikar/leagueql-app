# league-onboarding Specification

## Purpose
Onboard a new ESPN or Sleeper fantasy-football league into LeagueQL for the first time. `POST /leagues?requestType=ONBOARD` validates the request, creates a `JOB_STATUS` tracking item, and asynchronously invokes the onboarder Lambda, which fetches all historical season data, uploads raw payloads to S3, and hands off to the data-processing pipeline that writes precomputed views. A successful onboard produces a canonical league ID (UUID) unifying the league across seasons and platforms, a `METADATA` item, a `LEAGUE_LOOKUP` per platform league ID, and an incremented `LEAGUE_COUNT`.

## Requirements

### Requirement: Onboard a new league
The API SHALL accept an `ONBOARD` request for a not-yet-onboarded league, create a `JOB_STATUS` item, invoke the onboarder Lambda, and return `201`.

#### Scenario: Valid new league
- **WHEN** `POST /leagues?requestType=ONBOARD` is called for a valid, not-yet-onboarded league
- **THEN** the API returns `201` with `{ detail, data: { correlation_id } }` and invokes the onboarder Lambda

#### Scenario: Already onboarded
- **WHEN** an `ONBOARD` is issued for a league ID already present in `LEAGUE_LOOKUP`
- **THEN** the API returns `200` "League already onboarded" and does not re-run the pipeline

#### Scenario: Invalid league ID format
- **WHEN** the `leagueId` does not match `^\d+$`
- **THEN** the API returns `422`

### Requirement: Resolve renewed Sleeper seasons to the existing canonical league
The onboarder SHALL walk the Sleeper `previous_league_id` chain and, when a renewed-season league ID resolves to an already-onboarded canonical league, reuse that canonical rather than minting a new one.

#### Scenario: Renewal resolves to an existing canonical
- **WHEN** an `ONBOARD` of a renewed Sleeper season (new league ID) resolves via its `previous_league_id` chain to an already-onboarded canonical league
- **THEN** a new `LEAGUE_LOOKUP` is written for the new league ID pointing at the existing canonical, no second `METADATA` is written (owner/members preserved), and `LEAGUE_COUNT` is not incremented

#### Scenario: Chain resolves nothing
- **WHEN** the `previous_league_id` chain resolves to no existing canonical league
- **THEN** a fresh canonical league ID and a new `METADATA` are minted

#### Scenario: Offseason renewal not yet started
- **WHEN** a renewed Sleeper season of an already-onboarded league has not started yet
- **THEN** it is a no-op success that registers the new league ID as a **pending** `LEAGUE_LOOKUP` (mapped to the existing canonical, `pending_season` marker, no `seasons`) rather than failing with `NOT_STARTED`

### Requirement: Sleeper chain terminator handling
The onboarder SHALL terminate the `previous_league_id` chain walk at the founding season for both terminator forms and never issue a fetch for league `None`.

#### Scenario: String and null terminators
- **WHEN** the chain reaches a `previous_league_id` of the string `"0"` or JSON `null` (`None`), or any other falsy value
- **THEN** the walk terminates and no request is made for league `None`

### Requirement: Exclude not-yet-started Sleeper seasons
The onboarder SHALL exclude Sleeper seasons whose `status` is `pre_draft` or `drafting` from the onboarded season list, and SHALL fail a brand-new onboard whose only season is not-yet-started.

#### Scenario: Preseason season excluded
- **WHEN** a Sleeper season has `status` of `pre_draft` or `drafting`
- **THEN** it produces no S3 payload, no processed views, and no dropdown entry

#### Scenario: New league with only a not-started season
- **WHEN** a brand-new Sleeper onboard's only season has not started
- **THEN** onboarding fails with a friendly `NOT_STARTED` message rather than writing empty records

### Requirement: Exclude not-yet-drafted ESPN seasons
The onboarder SHALL exclude an ESPN season whose draft has not occurred (`draftDetail.drafted` is `false`) from the onboarded season list, and SHALL fail a brand-new ESPN onboard whose only season has not drafted with the same `NOT_STARTED` outcome used for not-yet-started Sleeper seasons. Because an ESPN league's completed prior seasons are the only ones reported as `previousSeasons`, the not-yet-drafted season can only be the latest season.

#### Scenario: Preseason latest season excluded from a multi-season league
- **WHEN** an ESPN league has one or more completed prior seasons plus a latest season whose `draftDetail.drafted` is `false`
- **THEN** the prior seasons onboard normally and the not-yet-drafted latest season produces no S3 payload, no processed views, and no season-dropdown entry

#### Scenario: New ESPN league whose only season has not drafted
- **WHEN** a brand-new ESPN onboard's only season has `draftDetail.drafted` of `false`
- **THEN** onboarding fails with the friendly `NOT_STARTED` message (templated for ESPN) rather than writing empty records, and no `draft_picks` view is registered for the processor

### Requirement: Tolerate a null Sleeper playoff bracket
The onboarder SHALL treat a successful null `winners_bracket`/`losers_bracket` body as valid (empty), while treating a genuine bracket fetch failure as a failed API call for that season (per the resilient-season behavior).

#### Scenario: Null bracket body
- **WHEN** a season's `winners_bracket`/`losers_bracket` endpoint returns a JSON `null` body
- **THEN** onboarding succeeds and that season yields no `PLAYOFF_BRACKET#{season}` view

#### Scenario: Genuine bracket fetch failure
- **WHEN** the bracket fetch fails (timeout/connection error/4xx → exception, `data: None`)
- **THEN** that season is skipped (no S3 payload, no processed views, no `seasons`-set entry); the remaining seasons still onboard, and the onboard fails as a whole only if that season was the only one

### Requirement: Protect ESPN credentials
ESPN onboards SHALL require `season`, private ESPN leagues SHALL require `s2` + `swid`, and `s2`/`swid` values SHALL NOT appear in logs or persisted DynamoDB/S3 items.

#### Scenario: ESPN input requirements
- **WHEN** an ESPN league is onboarded
- **THEN** `season` is required, and a private ESPN league additionally requires `s2` + `swid`

#### Scenario: Credentials never persisted
- **WHEN** private ESPN cookies are supplied for onboarding
- **THEN** the `s2`/`swid` values appear in no log line and no persisted DynamoDB or S3 item

### Requirement: Persist onboarded league data
On success the onboarder SHALL write the raw platform payloads to S3 and produce the canonical league artifacts, incrementing `LEAGUE_COUNT`.

#### Scenario: Successful onboard artifacts
- **WHEN** onboarding succeeds
- **THEN** a canonical league UUID, a `METADATA` item, a per-platform `LEAGUE_LOOKUP`, and all precomputed view items exist, and `LEAGUE_COUNT` is incremented by 1

#### Scenario: Raw payloads stored
- **WHEN** onboarding fetches platform data
- **THEN** the raw API payloads are written to S3 under `raw-api-data/{canonical_league_id}/`

### Requirement: Track job status
The API/onboarder SHALL create a `JOB_STATUS` item keyed by `correlation_id` and record failures on it.

#### Scenario: Job status created
- **WHEN** an onboard is triggered
- **THEN** a `JOB_STATUS` item keyed by `correlation_id` is created so the frontend can poll it

#### Scenario: Failure recorded
- **WHEN** onboarding fails for any reason (e.g. invalid ESPN credentials → `ESPN_AUTH`, platform unreachable, or every season failing to fetch)
- **THEN** the `JOB_STATUS` item is set to `status=FAILED` with a `failure_code`/`failure_reason` the frontend can surface

### Requirement: Dead-letter exhausted async invocations
When an async onboarder invocation exhausts its retries, the failed event SHALL be delivered to the onboarder dead-letter queue and raise an alarm rather than being dropped.

#### Scenario: Poison event exhausts retries
- **WHEN** an async onboarder invocation (`InvocationType="Event"`) exhausts Lambda's retries
- **THEN** the failed event is delivered to the onboarder DLQ (preserving the payload and `correlation_id`) and a CloudWatch alarm fires on DLQ depth > 0

### Requirement: Record the onboarding owner
The first `ONBOARD` SHALL record the onboarding Clerk user as the league owner and seed the `members` set; `REFRESH`/`MIGRATE` SHALL NOT overwrite it.

#### Scenario: Owner anchored on first onboard
- **WHEN** a league is onboarded for the first time
- **THEN** `owner_user_id` is set to the onboarding user and the `members` set is seeded, and later `REFRESH`/`MIGRATE` operations leave them unchanged

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

### Requirement: Persist the auto-refresh opt-in on onboard and refresh

When an onboard or refresh request carries an automatic-refresh opt-in choice, the onboarder SHALL
persist it as `auto_refresh_enabled` on the canonical league's `METADATA` item so the scheduled
refresh can honor it. The choice SHALL be preserved across a new-season refresh (it SHALL NOT be
reset when a renewed season is registered).

#### Scenario: Opt-in recorded on onboard

- **WHEN** an ESPN or Yahoo onboard/refresh request indicates the owner is enabling automatic refresh
- **THEN** the canonical league's `METADATA` `auto_refresh_enabled` is set to true

#### Scenario: Opt-out recorded on onboard

- **WHEN** an ESPN or Yahoo onboard/refresh request indicates automatic refresh is not enabled
- **THEN** the canonical league's `METADATA` `auto_refresh_enabled` is set to false

### Requirement: Store the owner's ESPN cookies when opting into auto-refresh

When an ESPN onboard or refresh opts into automatic refresh and completes successfully, the
onboarder SHALL store the owner's `SWID` and `espn_s2` cookies encrypted at rest so a later
scheduled refresh can reuse them, storing them only after the cookies have successfully fetched the
league's data.

#### Scenario: Cookies persisted after a successful opted-in ESPN onboard

- **WHEN** an ESPN onboard/refresh that opts into automatic refresh fetches the league successfully
- **THEN** the owner's ESPN cookies are stored encrypted for reuse by the scheduled refresh

#### Scenario: Cookies not persisted on failure

- **WHEN** an ESPN onboard/refresh that opts into automatic refresh fails to authenticate against ESPN
- **THEN** no ESPN cookies are stored

### Requirement: Use the owner's stored ESPN cookies for a scheduled refresh

When an ESPN refresh is invoked with an `owner_user_id` and no cookies (the scheduled-refresh path),
the onboarder SHALL fetch and decrypt that owner's stored ESPN cookies to perform the fetch, and
SHALL record the existing `ESPN_AUTH` failure (which does not page on-call) when the owner has no
stored cookies or the stored cookies no longer authenticate.

#### Scenario: Scheduled ESPN refresh uses stored cookies

- **WHEN** an ESPN refresh is invoked with an `owner_user_id` and no cookies in the request
- **THEN** the onboarder fetches and decrypts that owner's stored ESPN cookies and uses them to
  refresh the league

#### Scenario: Missing or expired stored cookies

- **WHEN** a scheduled ESPN refresh finds no stored cookies for the owner, or the stored cookies are
  rejected by ESPN
- **THEN** the refresh records an `ESPN_AUTH` failure without paging on-call

### Requirement: Onboard seasons resiliently
The onboarder SHALL onboard every season whose API calls all succeeded and SHALL skip a
season for which any API call failed (fetch exception, timeout, connection error, or
`4xx`/`5xx`), rather than failing the whole onboard. It SHALL fail the onboard as a whole
only when **every** season failed. A skipped season SHALL produce no S3 payload, no
processed views, and no entry in the league's recorded `seasons` set — as if it had not
been requested. This applies to all platforms (ESPN, Sleeper, Yahoo). A `REFRESH`, which
fetches only the current season, therefore fails when that single season fails
(unchanged), because it is the all-seasons-failed case.

#### Scenario: Mixed multi-season league onboards the accessible seasons
- **WHEN** a multi-season onboard fetches several seasons and one or more seasons have at
  least one failed API call while at least one other season's calls all succeed
- **THEN** the fully-successful seasons onboard normally (raw S3 payloads, processed
  views, `seasons`-set entries) and the failed seasons produce no S3 payload, no
  processed views, and no `seasons`-set entry, and the onboard returns success

#### Scenario: All seasons fail
- **WHEN** every season being onboarded has at least one failed API call
- **THEN** onboarding fails as a whole (the existing `UPSTREAM`/`502` outcome) and no
  `METADATA` item is written for the league
