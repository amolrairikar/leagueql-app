## Context

See proposal.md — Why. The scheduled `leagueql-sleeper-refresh` Lambda (EventBridge `cron(0 13 ? * TUE *)`, east-only) enumerates Sleeper leagues and dispatches an async (`InvocationType="Event"`) onboarder invocation per league in a back-to-back loop in `src/sleeper_refresh/handler.py`. There is no queue in the forward path (only an onboarder DLQ). Two constraints shape the design:

- The **onboarder** Lambda's timeout is 30s and it is the *shared* worker for user-facing onboarding — there is no room to sleep there, and adding delay would slow the interactive path.
- The **dispatcher** currently has a 60s timeout.

## Goals / Non-Goals

**Goals:**
- Spread the moment each onboarder (and thus its Sleeper API burst) starts across a randomized, bounded window.
- Keep the change isolated to the dispatcher; leave the onboarder, the invoke contract, and user-facing onboarding untouched.
- Make the window configurable and trivially disable-able (for tests / emergencies).

**Non-Goals:**
- No new infrastructure (no SQS forward queue, no Step Functions, no EventBridge Scheduler).
- No change to league selection, correlation-id tracing, or failure/retry semantics.
- Not attempting to rate-limit the Sleeper API precisely — jitter de-clusters load; it does not enforce a strict RPS.

## Decisions

**Jitter in the dispatcher, via in-process sleeps.** The dispatcher owns *when* each async onboarder invoke fires, so spreading the invokes there directly spreads the Sleeper load. Chosen over: (a) onboarder-side sleep — infeasible given the shared 30s onboarder; (b) an SQS delay queue with per-message `DelaySeconds` — the "proper" pattern and avoids idle Lambda billing, but requires a new queue, IAM, event-source mapping, rewiring `common/onboarder_invoke.py`, and onboarder changes to consume SQS records, plus architecture-diagram/spec/test churn — disproportionate for a weekly, no-urgency job on a small league set.

**Bounded random-offset algorithm.** Draw one `random.uniform(0, window)` offset per league, sort ascending, and `time.sleep` the delta between consecutive offsets (first sleep = smallest offset). This bounds total wall-clock to ≤ window regardless of league count and randomizes both ordering and arrival times (true jitter). Chosen over a fixed even spacing (`window / n` — deterministic, not "jitter") and over per-iteration `uniform(0, gap)` (total unbounded, risks exceeding the timeout).

**Configurable window via `REFRESH_JITTER_WINDOW_SECONDS` (default 600).** `0` disables jitter (preserves today's behavior; used by tests so they never actually sleep). A single-league run also skips jitter (a random up-to-10-min delay for one league is pure waste). Read once at dispatch time.

**Timeout bump 60s → 900s** (`infrastructure/regional/main.tf`, `module "sleeper_refresh_lambda"`). Lambda's 15-min max comfortably exceeds the 600s window plus the NFL-state fetch, DynamoDB query, and final invoke. The env var and timeout are set together, with a comment tying them.

## Risks / Trade-offs

- **Dispatcher billed while sleeping** (≤ ~10 min of a 512 MB Lambda, once a week) → negligible; the cost of avoiding new infra.
- **A window set larger than the timeout would truncate the run** → keep the Terraform env var and timeout consistent (600s window under a 900s timeout) and document the relationship in a comment.
- **Retry re-dispatches the whole run** (existing raise-after-loop behavior; a dispatcher error mid-window makes EventBridge retry) → acceptable: `REFRESH` is idempotent, so re-refreshing already-dispatched leagues only wastes work.
- **Tests must not actually sleep** → run unit and component tests with the window at `0` (or patch `time.sleep`); assert spread/order logic in unit tests, keep wall-clock assertions out of component tests.
