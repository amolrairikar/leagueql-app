## Purpose
Scheduled backend job that removes leagues nobody has opened for a year, to limit storage costs.

## ADDED Requirements

### Requirement: Run nightly in production only
The reaper SHALL run once per day on a nightly schedule and SHALL be deployed only in production, in a single region.

#### Scenario: Nightly production run
- **WHEN** the nightly schedule fires in production
- **THEN** the reaper evaluates every league listed by the GSI3 all-leagues index, across all result pages

#### Scenario: Non-production environment
- **WHEN** infrastructure is applied to a non-production environment
- **THEN** no reaper is deployed

### Requirement: Remove only leagues idle for one calendar year
A league SHALL be eligible for removal only when the current time is at least one calendar year after its `last_accessed_at`, or after its `onboarded_at` when `last_accessed_at` is absent; timestamps without a timezone SHALL be treated as UTC, and a February 29 anniversary SHALL fall on March 1.

#### Scenario: Never opened and onboarded a year ago
- **WHEN** a league has no `last_accessed_at` and was onboarded exactly one calendar year ago
- **THEN** it is eligible

#### Scenario: Idle since its last access
- **WHEN** a league's `last_accessed_at` is at least one calendar year old
- **THEN** it is eligible

#### Scenario: Old league still being opened
- **WHEN** a league was onboarded more than a year ago but accessed within the last year
- **THEN** it is kept, even if `last_accessed_at` is more than a year after `onboarded_at`

#### Scenario: Just under a year
- **WHEN** a league's latest activity is less than one calendar year old
- **THEN** it is kept

#### Scenario: Leap day
- **WHEN** a league's latest activity was on February 29
- **THEN** it becomes eligible on March 1 of the following year

#### Scenario: Unusable timestamps
- **WHEN** `onboarded_at` is missing or unparseable, or `last_accessed_at` is present but unparseable
- **THEN** the league is kept

### Requirement: Default to a dry run
The reaper SHALL delete nothing and write nothing unless its dry-run setting is exactly `false` (case-insensitive).

#### Scenario: Setting absent or unrecognized
- **WHEN** the dry-run setting is unset or any value other than `false`
- **THEN** eligible leagues are only reported and no data is modified

#### Scenario: Deletion enabled
- **WHEN** the dry-run setting is `false`
- **THEN** eligible leagues are removed

### Requirement: Re-check each league before removal
Before removing a league, the reaper SHALL re-read its `METADATA` with a strongly consistent read and SHALL skip it when the item is gone, it is no longer eligible, a job for it is in progress, or a lineup backfill lease on it has not expired.

#### Scenario: Opened after the index was read
- **WHEN** the consistent re-read shows a recent `last_accessed_at`
- **THEN** the league is not removed

#### Scenario: Job or backfill in progress
- **WHEN** the league's active job is `IN_PROGRESS` or its `lineup_backfill_lease_until` is in the future
- **THEN** the league is skipped and counted as skipped

### Requirement: Remove all of a league's data
The reaper SHALL remove every raw S3 object under `raw-api-data/{canonical_league_id}/` and then every DynamoDB item of the league, including all `LEAGUE_LOOKUP` and member items, removing `METADATA` last so an incomplete removal is retried on a later run.

#### Scenario: Idle league removed
- **WHEN** an eligible league is removed
- **THEN** no raw S3 objects, lookup items, member items, views, or `METADATA` remain for it

#### Scenario: S3 deletion fails
- **WHEN** deleting a league's raw S3 data fails
- **THEN** its DynamoDB items are left in place

### Requirement: Clean up orphaned platform credentials
After removing a league, the reaper SHALL remove the owner's stored `YAHOO_OAUTH` or `ESPN_CREDENTIALS` item under the same rules as a manual delete (backend/delete-league), disregarding every league already removed in the same run, and a cleanup failure SHALL NOT undo or fail the removal.

#### Scenario: Owner loses their last league needing credentials
- **WHEN** all of an owner's Yahoo leagues (or opted-in ESPN leagues) are removed, including several in one run
- **THEN** the corresponding stored credential item is removed

#### Scenario: Owner still needs the credentials
- **WHEN** the owner has another Yahoo league (or another opted-in ESPN league)
- **THEN** the credential item is kept

#### Scenario: Cleanup fails
- **WHEN** credential cleanup raises an error
- **THEN** the league still counts as removed and the summary reports the cleanup failure

### Requirement: Isolate failures and finish cleanly
One league's failure SHALL NOT stop the others, the run SHALL raise after reporting when any removal failed, and the reaper SHALL NOT start another removal when under 60 seconds of execution time remain. There SHALL be no per-run limit on the number of removals.

#### Scenario: One removal fails
- **WHEN** removing one of several eligible leagues fails
- **THEN** the others are still removed, the summary reports the failure, and the run raises

#### Scenario: Running out of time
- **WHEN** under 60 seconds remain
- **THEN** the remaining eligible leagues are left for a later run and reported as deferred

### Requirement: Post a Discord summary
When any league was eligible, the reaper SHALL post one Discord summary stating whether it was a dry run, the counts of removed (or removable), skipped, failed, and deferred leagues, and each league's name, platform, canonical ID, and last activity, truncated to fit Discord's limits; it SHALL post nothing when no league was eligible, SHALL log every eligible league, and SHALL raise before removing anything when the webhook is not configured. Lines for removal failures and credential cleanup failures SHALL be listed before the league lines, so truncation drops leagues first.

#### Scenario: Eligible leagues reported
- **WHEN** a run finds eligible leagues
- **THEN** it posts one summary labeled as a dry run or a removal run

#### Scenario: Nothing eligible
- **WHEN** no league is eligible
- **THEN** no Discord message is posted

#### Scenario: Long list
- **WHEN** the league lines exceed the Discord embed limit
- **THEN** the list is truncated and states how many more there are

#### Scenario: Webhook not configured
- **WHEN** the Discord webhook URL is not configured
- **THEN** the run raises without removing any league

#### Scenario: Problems in a long list
- **WHEN** a run with a removal failure or a credential cleanup failure has more league lines than fit
- **THEN** the problem lines appear at the top of the summary and only league lines are truncated
