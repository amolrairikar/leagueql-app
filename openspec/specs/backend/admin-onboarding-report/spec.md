# admin-onboarding-report Specification

## Purpose
Scheduled backend job that periodically aggregates onboarding-health metrics from the DynamoDB
METADATA items and pushes a formatted digest to an admin Discord channel, so onboarding trends are
surfaced automatically instead of only through a manually-run dashboard.

## Requirements

### Requirement: Nightly onboarding-health digest
The job SHALL run on a nightly schedule, query the GSI3 all-leagues index for every METADATA item
(paginating until exhausted), and post exactly one Discord message reporting the total leagues
onboarded, the number of active leagues (accessed within the last 14 days), the ESPN-vs-SLEEPER
split, and the count of new leagues onboarded within the last 24 hours, 7 days, and 30 days.

#### Scenario: Nightly run posts the digest
- **WHEN** the scheduled run executes and the query returns onboarded leagues
- **THEN** it posts a single Discord message containing the total onboarded count, the active-leagues (14d) count, the ESPN and SLEEPER counts, and the 24h/7d/30d new-onboard counts

#### Scenario: All METADATA items are counted across pages
- **WHEN** the GSI3 query returns results across multiple pages (a `LastEvaluatedKey` is present)
- **THEN** the run continues paginating and aggregates every METADATA item into the reported counts

#### Scenario: No onboarded leagues
- **WHEN** the query returns no METADATA items
- **THEN** the run still posts a digest with all counts equal to zero rather than raising

### Requirement: Metric semantics
The job SHALL treat `active_platform` as the authoritative platform when present (falling back to
`platform`), count a league as active only when its `last_accessed_at` is within the trailing
14-day window, and exclude any league whose `onboarded_at` is missing or unparseable from the
total and the new-onboard windows.

#### Scenario: Migrated league counts under its active platform
- **WHEN** a league has `platform = "ESPN"` and `active_platform = "SLEEPER"`
- **THEN** it is counted as a SLEEPER league in the platform split

#### Scenario: Missing last_accessed_at is inactive
- **WHEN** a league has no `last_accessed_at` value
- **THEN** it is not counted toward the active-leagues (14d) total

#### Scenario: Active window boundary is inclusive
- **WHEN** a league was last accessed exactly 14 days before the run time
- **THEN** it is counted as active

#### Scenario: Unparseable onboarded_at is excluded
- **WHEN** a league's `onboarded_at` is missing or not a parseable timestamp
- **THEN** it is excluded from the total onboarded count and from every new-onboard window

### Requirement: Failure surfaces without re-alerting
The job SHALL raise on a DynamoDB-query failure, on a non-success Discord webhook response, or when
the webhook is not configured, so the error is recorded in its own execution/error metrics; it
SHALL NOT publish the failure to the shared alert notification topic.

#### Scenario: DynamoDB query fails
- **WHEN** the GSI3 query raises an error
- **THEN** the run raises (posting no digest) so the failure is recorded in its own error metrics

#### Scenario: Discord webhook returns an error
- **WHEN** the Discord webhook responds with a non-success status
- **THEN** the run raises so the failure is recorded in its own error metrics

#### Scenario: Webhook not configured
- **WHEN** the Discord webhook URL is not configured
- **THEN** the run raises rather than silently completing

#### Scenario: Failure is not re-published to the alert topic
- **WHEN** the run fails for any reason
- **THEN** it does not publish the failure to the shared alert notification topic (avoiding an alert loop)
