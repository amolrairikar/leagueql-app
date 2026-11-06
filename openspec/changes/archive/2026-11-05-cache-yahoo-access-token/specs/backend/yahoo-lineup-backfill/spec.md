## MODIFIED Requirements

### Requirement: Pace Yahoo requests and limit concurrent backfills
The backfill SHALL send its Yahoo requests one at a time at a steady, low rate. No more than two
backfill runs SHALL execute at the same time across all leagues. Within a run, the backfill SHALL
resolve the owner's Yahoo access token once and reuse it across requests (re-resolving only near
expiry or after a `401`), so the number of token decrypts does not grow with the number of requests.

#### Scenario: Paced requests
- **WHEN** a season backfill fetches 192 rosters
- **THEN** the requests are sent one after another at about one per second, never in parallel

#### Scenario: Concurrency cap
- **WHEN** many leagues have queued backfills
- **THEN** at most two backfill runs execute at a time and the rest wait in the queue

#### Scenario: One token resolution per run
- **WHEN** a season backfill fetches 192 rosters within the token's validity
- **THEN** the owner's stored Yahoo token is read and decrypted once, not 192 times

#### Scenario: Token expires during a long season
- **WHEN** a season backfill runs long enough for the owner's access token to reach its expiry skew
- **THEN** the backfill obtains a fresh token and continues, still resolving the token far fewer times than it sends requests

#### Scenario: Unauthorized response mid-run
- **WHEN** Yahoo answers a roster request with `401`
- **THEN** the backfill re-resolves the owner's token and retries that request once; a second `401` stops the backfill as a permanent error as before
