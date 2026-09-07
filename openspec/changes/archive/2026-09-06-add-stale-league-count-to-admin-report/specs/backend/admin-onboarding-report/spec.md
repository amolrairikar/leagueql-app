## MODIFIED Requirements

### Requirement: Nightly onboarding-health digest
The job SHALL run on a nightly schedule, query the GSI3 all-leagues index for every METADATA item
(paginating until exhausted), and post exactly one Discord message reporting the total leagues
onboarded, the number of active leagues (accessed within the last 14 days), the number of stale
leagues (not refreshed within the last 365 days), the ESPN-vs-SLEEPER split, and the count of new
leagues onboarded within the last 24 hours, 7 days, and 30 days.

#### Scenario: Nightly run posts the digest
- **WHEN** the scheduled run executes and the query returns onboarded leagues
- **THEN** it posts a single Discord message containing the total onboarded count, the active-leagues (14d) count, the stale-leagues (1y) count, the ESPN and SLEEPER counts, and the 24h/7d/30d new-onboard counts

#### Scenario: All METADATA items are counted across pages
- **WHEN** the GSI3 query returns results across multiple pages (a `LastEvaluatedKey` is present)
- **THEN** the run continues paginating and aggregates every METADATA item into the reported counts

#### Scenario: No onboarded leagues
- **WHEN** the query returns no METADATA items
- **THEN** the run still posts a digest with all counts equal to zero rather than raising

### Requirement: Metric semantics
The job SHALL treat `active_platform` as the authoritative platform when present (falling back to
`platform`), count a league as active only when its `last_accessed_at` is within the trailing
14-day window, count a league as stale only when its `last_refresh_at` — falling back to
`onboarded_at` when it has never been refreshed — is strictly more than 365 days before the run
time, and exclude any league whose `onboarded_at` is missing or unparseable from the total and the
new-onboard windows.

#### Scenario: Migrated league counts under its active platform
- **WHEN** a league has `platform = "ESPN"` and `active_platform = "SLEEPER"`
- **THEN** it is counted as a SLEEPER league in the platform split

#### Scenario: Missing last_accessed_at is inactive
- **WHEN** a league has no `last_accessed_at` value
- **THEN** it is not counted toward the active-leagues (14d) total

#### Scenario: Active window boundary is inclusive
- **WHEN** a league was last accessed exactly 14 days before the run time
- **THEN** it is counted as active

#### Scenario: Stale count uses last_refresh_at over a year old
- **WHEN** a league's `last_refresh_at` is more than 365 days before the run time
- **THEN** it is counted toward the stale-leagues (1y) total

#### Scenario: Never-refreshed league falls back to onboarded_at
- **WHEN** a league has no `last_refresh_at` and its `onboarded_at` is more than 365 days before the run time
- **THEN** it is counted as stale

#### Scenario: Recently refreshed league is not stale despite old onboarded_at
- **WHEN** a league's `onboarded_at` is over a year old but its `last_refresh_at` is within the last 365 days
- **THEN** it is not counted as stale

#### Scenario: Stale window boundary is exclusive
- **WHEN** a league's reference timestamp is exactly 365 days before the run time
- **THEN** it is not counted as stale

#### Scenario: League with no parseable timestamps is not stale
- **WHEN** a league has neither a parseable `last_refresh_at` nor a parseable `onboarded_at`
- **THEN** it is excluded from the stale-leagues count

#### Scenario: Unparseable onboarded_at is excluded
- **WHEN** a league's `onboarded_at` is missing or not a parseable timestamp
- **THEN** it is excluded from the total onboarded count and from every new-onboard window
