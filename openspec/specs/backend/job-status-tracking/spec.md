# job-status-tracking Specification

## Purpose
Track the lifecycle of asynchronous onboard/refresh/migrate jobs so the frontend can poll for completion or failure. Each triggered job creates a `JOB_STATUS` DynamoDB item keyed by its `correlation_id`. `GET /jobs/{jobId}` returns the current status plus a user-friendly failure reason when the job failed.

## Requirements

### Requirement: Return job status
The API SHALL return the status and failure fields for a job item.

#### Scenario: Existing job
- **WHEN** `GET /jobs/{jobId}` is called for an existing job item
- **THEN** the API returns `{ status, failure_code, failure_reason }`

#### Scenario: Missing or expired job
- **WHEN** the job item never existed or its 24h TTL has expired
- **THEN** the API returns `200` with `status=FAILED` so the frontend stops polling

### Requirement: Classify failures
`FAILED` jobs SHALL carry a non-null machine-readable `failure_code` and a human-readable `failure_reason` that names the relevant platform; non-failed jobs SHALL have them null.

#### Scenario: Failed job classification
- **WHEN** a job has failed (e.g. ESPN credential rejection)
- **THEN** it carries a non-null `failure_code` (e.g. `ESPN_AUTH`) and a `failure_reason` referencing the platform

#### Scenario: Non-failed job
- **WHEN** a job is `IN_PROGRESS` or `COMPLETED`
- **THEN** `failure_code` and `failure_reason` are null

### Requirement: Create job items at trigger time
Onboard, refresh, and migrate SHALL each create a `JOB_STATUS` item keyed by `correlation_id` with a 24h TTL.

#### Scenario: Job created on trigger
- **WHEN** an onboard, refresh, or migrate is triggered
- **THEN** a `JOB_STATUS` item keyed by `correlation_id` is created with a 24h TTL

#### Scenario: Long-running job stays in progress
- **WHEN** a large league is still processing
- **THEN** the status remains `IN_PROGRESS` until the processor commits

### Requirement: No-store caching
The API SHALL respond with `Cache-Control: no-store`.

#### Scenario: Cache header
- **WHEN** the job-status endpoint responds
- **THEN** it sets `Cache-Control: no-store`
