# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Tolerate a null Sleeper playoff bracket
The onboarder SHALL treat a successful null `winners_bracket`/`losers_bracket` body as valid (empty), while treating a genuine bracket fetch failure as a failed API call for that season (per the resilient-season behavior).

#### Scenario: Null bracket body
- **WHEN** a season's `winners_bracket`/`losers_bracket` endpoint returns a JSON `null` body
- **THEN** onboarding succeeds and that season yields no `PLAYOFF_BRACKET#{season}` view

#### Scenario: Genuine bracket fetch failure
- **WHEN** the bracket fetch fails (timeout/connection error/4xx → exception, `data: None`)
- **THEN** that season is skipped (no S3 payload, no processed views, no `seasons`-set entry); the remaining seasons still onboard, and the onboard fails as a whole only if that season was the only one

### Requirement: Track job status
The API/onboarder SHALL create a `JOB_STATUS` item keyed by `correlation_id` and record failures on it.

#### Scenario: Job status created
- **WHEN** an onboard is triggered
- **THEN** a `JOB_STATUS` item keyed by `correlation_id` is created so the frontend can poll it

#### Scenario: Failure recorded
- **WHEN** onboarding fails for any reason (e.g. invalid ESPN credentials → `ESPN_AUTH`, platform unreachable, or every season failing to fetch)
- **THEN** the `JOB_STATUS` item is set to `status=FAILED` with a `failure_code`/`failure_reason` the frontend can surface
