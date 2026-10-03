## MODIFIED Requirements

### Requirement: Use the owner's stored ESPN cookies for a scheduled refresh

When an ESPN refresh is invoked with an `owner_user_id` and no cookies (the scheduled-refresh path),
the onboarder SHALL fetch and decrypt that owner's stored ESPN cookies to perform the fetch, and
SHALL record the existing `ESPN_AUTH` failure (which does not page on-call) when the owner has no
stored cookies or the stored cookies no longer authenticate. When the stored cookies were rejected,
the onboarder SHALL also flag them as rejected (backend/espn-credential-storage), best-effort.

#### Scenario: Scheduled ESPN refresh uses stored cookies

- **WHEN** an ESPN refresh is invoked with an `owner_user_id` and no cookies in the request
- **THEN** the onboarder fetches and decrypts that owner's stored ESPN cookies and uses them to
  refresh the league

#### Scenario: Missing or expired stored cookies

- **WHEN** a scheduled ESPN refresh finds no stored cookies for the owner, or the stored cookies are
  rejected by ESPN
- **THEN** the refresh records an `ESPN_AUTH` failure without paging on-call

#### Scenario: Rejected stored cookies flagged for the owner

- **WHEN** a scheduled ESPN refresh's stored cookies are rejected by ESPN (the season lookup or every
  data fetch returns `401`/`403`)
- **THEN** the onboarder marks the owner's stored credentials with `auth_failed_at`, and a failure to
  write that mark is logged without changing the recorded `ESPN_AUTH` failure

#### Scenario: User-supplied cookies are never flagged

- **WHEN** an ESPN onboard or refresh that supplied cookies in the request is rejected by ESPN
- **THEN** the stored credentials are not marked

### Requirement: Onboard seasons resiliently
The onboarder SHALL onboard every season whose API calls all succeeded and SHALL skip a
season for which any API call failed (fetch exception, timeout, connection error, or
`4xx`/`5xx`), rather than failing the whole onboard. It SHALL fail the onboard as a whole
only when **every** season failed. A skipped season SHALL produce no S3 payload, no
processed views, and no entry in the league's recorded `seasons` set — as if it had not
been requested. This applies to all platforms (ESPN, Sleeper, Yahoo). A `REFRESH`, which
fetches only the current season, therefore fails when that single season fails
(unchanged), because it is the all-seasons-failed case. When every season failed and every
failed request was rejected with `401`/`403`, an ESPN onboard or refresh SHALL record
`ESPN_AUTH` (which does not page on-call) instead of `UPSTREAM`.

#### Scenario: Mixed multi-season league onboards the accessible seasons
- **WHEN** a multi-season onboard fetches several seasons and one or more seasons have at
  least one failed API call while at least one other season's calls all succeed
- **THEN** the fully-successful seasons onboard normally (raw S3 payloads, processed
  views, `seasons`-set entries) and the failed seasons produce no S3 payload, no
  processed views, and no `seasons`-set entry, and the onboard returns success

#### Scenario: All seasons fail
- **WHEN** every season being onboarded has at least one failed API call and at least one
  failure was not a `401`/`403`
- **THEN** onboarding fails as a whole (the existing `UPSTREAM`/`502` outcome) and no
  `METADATA` item is written for the league

#### Scenario: All seasons rejected for auth
- **WHEN** every season of an ESPN onboard or refresh failed and every failed request returned
  `401`/`403`
- **THEN** the job records `ESPN_AUTH`, no on-call alert is published, and no `METADATA` item is
  written for the league
