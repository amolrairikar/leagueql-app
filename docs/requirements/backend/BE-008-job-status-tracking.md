# BE-008: Job Status Tracking

## Description
Tracks the lifecycle of asynchronous onboard/refresh/migrate jobs so the frontend can poll
for completion or failure. Each triggered job creates a `JOB_STATUS` DynamoDB item keyed by
its `correlation_id`. `GET /jobs/{jobId}` returns the current status plus a user-friendly
failure reason when the job failed.

## Scope
- Endpoint: `GET /jobs/{jobId}` (`src/api/routes.py::get_job`).
- Item: `JOB_STATUS` keyed by `correlation_id`, with a 24h TTL.
- Writers: `src/common/job_status.py` (`write_job_status`, `classify_http_error`),
  invoked by the API, onboarder, and processor Lambdas.
- Statuses: `IN_PROGRESS`, `COMPLETED`, `FAILED`.

## Edge Cases
- **Missing item (never created, or TTL-expired after 24h):** reported as `FAILED` so the
  frontend stops polling.
- **Failure classification:** failures carry a machine-readable `failure_code`
  (e.g. `ESPN_AUTH`) and a human-readable `failure_reason`.
- **Long-running jobs:** large leagues can take ~120s+; status stays `IN_PROGRESS` until
  the processor commits.
- **Error messages name the platform:** failure reasons should reference the relevant
  platform (e.g. "ESPN rejected your credentials…"). (See git history: error messaging.)
- **Caching:** the endpoint must respond `Cache-Control: no-store` (polled frequently).
- **Job status lives in its own item:** failure reason is on the `JOB_STATUS` item keyed by
  `correlation_id`, not on `METADATA`. (See memory: JOB_STATUS item.)

## Acceptance Criteria
- [ ] `GET /jobs/{jobId}` returns `{ status, failure_code, failure_reason }` for an existing
      job item.
- [ ] A missing or TTL-expired job returns `200` with `status=FAILED`.
- [ ] `FAILED` jobs include a non-null `failure_code` and `failure_reason`; non-failed jobs
      have them null.
- [ ] Onboard, refresh, and migrate all create a `JOB_STATUS` item at trigger time.
- [ ] Response sets `Cache-Control: no-store`.
- [ ] `JOB_STATUS` items carry a 24h TTL.

## Sources
`src/api/routes.py::get_job`, `src/common/job_status.py`, memory: `project_job_status_item`.
