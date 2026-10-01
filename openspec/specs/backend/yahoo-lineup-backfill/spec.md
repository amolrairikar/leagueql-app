# backend/yahoo-lineup-backfill Specification

## Purpose
Fill in Yahoo weekly lineups and player points after onboarding, using a queued, paced, resumable
job that stays under Yahoo's rate limit. It tracks which seasons are still pending or have failed,
so users get every season right away and lineup detail follows.

## Requirements

### Requirement: Backfill one season at a time, newest first
The backfill SHALL process one lineup-pending season of a league per run, choosing the most recent
pending season. When that season is complete and more seasons are still pending, it SHALL queue the
next run for the league.

#### Scenario: Newest pending season first
- **WHEN** a league has lineup-pending seasons 2018, 2019, and 2026
- **THEN** the backfill processes 2026 first, then 2019, then 2018

#### Scenario: Nothing pending
- **WHEN** a backfill run starts for a league with no lineup-pending seasons
- **THEN** it makes no Yahoo requests and finishes without queueing another run

### Requirement: Fetch only completed, missing weeks
For a season, the backfill SHALL fetch each team's weekly roster and player points only for weeks
whose matchups are finished and that are not already in the season's lineup store.

#### Scenario: Completed season
- **WHEN** a finished 12-team, 16-week season with no lineup store is backfilled
- **THEN** the backfill fetches 12 × 16 per-team weekly rosters and stores every team's weekly
  lineup and player points

#### Scenario: In-progress season adds only new weeks
- **WHEN** the current season already has lineups stored for weeks 1–3 and week 4 has just finished
- **THEN** the backfill fetches only week 4's per-team rosters

#### Scenario: Unfinished week skipped
- **WHEN** a week's matchups are not started or still in progress
- **THEN** the backfill does not fetch that week's rosters

### Requirement: Pace Yahoo requests and limit concurrent backfills
The backfill SHALL send its Yahoo requests one at a time at a steady, low rate. No more than two
backfill runs SHALL execute at the same time across all leagues.

#### Scenario: Paced requests
- **WHEN** a season backfill fetches 192 rosters
- **THEN** the requests are sent one after another at about one per second, never in parallel

#### Scenario: Concurrency cap
- **WHEN** many leagues have queued backfills
- **THEN** at most two backfill runs execute at a time and the rest wait in the queue

### Requirement: Run at most one backfill per league at a time
The backfill SHALL hold a time-limited lease on the league while it runs. A run that finds another
run's unexpired lease SHALL exit without making Yahoo requests.

#### Scenario: Duplicate run skipped
- **WHEN** a second backfill run starts for a league whose lease is held and not expired
- **THEN** the second run exits immediately without fetching or writing anything

#### Scenario: Expired lease taken over
- **WHEN** a run starts for a league whose previous lease has expired (for example, the earlier
  run timed out)
- **THEN** the new run takes the lease and continues the backfill

### Requirement: Save progress and resume
The backfill SHALL save the weeks it has fetched to the season's lineup store as it goes, so a run
that stops early resumes without fetching those weeks again.

#### Scenario: Resume after interruption
- **WHEN** a run stored weeks 1–9 of a season before being throttled or timing out
- **THEN** the next run for that season fetches only weeks 10 onward

### Requirement: Back off when Yahoo throttles
When Yahoo returns HTTP `999`, the backfill SHALL stop sending requests immediately, save its
progress, and queue a retry for the league about 15 minutes later. After 8 consecutive throttled
attempts on the same season, it SHALL mark that season failed and move on to the next pending
season after the delay.

#### Scenario: Throttled mid-season
- **WHEN** Yahoo returns `999` partway through a season
- **THEN** the backfill sends no further requests in that run, keeps the weeks already fetched,
  and a retry runs about 15 minutes later

#### Scenario: Retries exhausted
- **WHEN** a season has been throttled on 8 consecutive attempts
- **THEN** the season moves from lineup-pending to failed lineup seasons, and the backfill
  continues with the next pending season

### Requirement: Stop on permanent errors
When the owner's Yahoo authorization is revoked, the league can't be accessed (`403`/`404`), or
the league has been deleted, the backfill SHALL stop that league's backfill without retrying. If
the league still exists, it SHALL mark the season failed.

#### Scenario: Yahoo link revoked
- **WHEN** the owner's Yahoo refresh token has been revoked
- **THEN** the backfill marks the season failed and queues no retry

#### Scenario: League deleted meanwhile
- **WHEN** the league was deleted after the backfill was queued
- **THEN** the run exits without fetching or writing anything

### Requirement: Publish a completed season
When all of a season's finished weeks are in its lineup store, the backfill SHALL have the
processor rebuild only that season (`backend/data-processing-pipeline` "Select seasons to
process"). It SHALL then remove the season from the league's lineup-pending seasons.

#### Scenario: Season published
- **WHEN** the backfill completes season 2024
- **THEN** the processor rebuilds only 2024 with lineups attached, and 2024 is no longer
  lineup-pending

#### Scenario: Concurrent refresh not lost
- **WHEN** a refresh adds a new season to the league while a backfill is publishing an older
  season
- **THEN** both the new season and the older season's rebuild take effect

### Requirement: Alert on repeatedly failing backfill messages
A backfill message that fails to process 3 times SHALL be moved to a dead-letter queue, and a
non-empty dead-letter queue SHALL alert the operators' alert channel.

#### Scenario: Poison message
- **WHEN** a backfill message errors on 3 deliveries
- **THEN** it lands in the dead-letter queue and an alert is sent
