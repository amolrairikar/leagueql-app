# BE-022: AI Weekly Matchup Recap

## Description
Generates an **AI-written weekly recap column** for each completed week of a league's matchups —
medium-long, lighthearted-but-journalistic prose with roasts where warranted — from the existing
precomputed matchup highlights, and caches it in DynamoDB as a `MATCHUP_RECAP#{season}#WEEK#{week}`
item. The frontend ([FE-037](../frontend/FE-037-weekly-matchup-recap.md)) reads the cached text
through the existing query API ([BE-005](BE-005-query-precomputed-views-api.md)); generation never
happens on the request path.

This is the repo's first **AWS Bedrock / LLM** integration. Recaps are generated **entirely via
Bedrock batch inference** (asynchronous `CreateModelInvocationJob`), not real-time `Converse`. Batch
runs on a **separate service-quota lane** from on-demand throughput, so it sidesteps the very low
real-time requests-per-minute quota for **Meta Llama 3.3 70B Instruct** (8 RPM, **not increasable in
the Bedrock console** for this model) that would otherwise throttle concurrent generation when
several leagues subscribe in the same window. The in-process per-task RPM rate limiter is therefore
**gone** — batch has its own quota and your code never paces calls. The model is
`us.meta.llama3-3-70b-instruct-v1:0` (US cross-region inference profile; the bare foundation-model id
fails on-demand), parameterized by the `BEDROCK_MODEL_ID` env var.

**Nothing is generated synchronously** — including for a just-subscribed league. Every recap is
produced by a batch job and lands asynchronously, so FE-037 shows a **"recaps generating"** state for
weeks that do not yet have a `MATCHUP_RECAP` item (rather than treating absence as missing data).
Typical end-to-end latency is the **drain interval + Bedrock batch turnaround** (tens of minutes,
occasionally longer under contention); batch carries no SLA.

The pipeline is **three decoupled stages**, all premium-gated + idempotent, with **no long-running
compute**:
1. **Enqueue** — the Stripe webhook (activation) and the processor (onboard/refresh completion) record
   a lightweight pending-work marker; they no longer launch any generation compute.
2. **Drain + submit** — a **scheduled Lambda** aggregates pending work **across all leagues** into one
   batch job (clearing Bedrock's minimum-records-per-job floor and amortizing job-startup overhead)
   and submits it.
3. **Completion** — an **EventBridge** rule on the Bedrock *Batch Inference Job State Change* event
   triggers a Lambda that reads the job output from S3 and writes the `MATCHUP_RECAP` items.

The **ECS Fargate task is retired**: batch moves all the waiting onto Bedrock's side, so the >15-min
concern that justified Fargate (a paced synchronous backfill exceeding the Lambda cap) no longer
exists, and every stage is short-lived and Lambda-friendly.

## Scope
- **Bedrock helper — `src/common/bedrock.py`** (vendored into both recap Lambdas). A module-level
  `boto3.client("bedrock-runtime")` plus a control-plane client for job submission. Batch input/output
  uses **InvokeModel-style `modelInput`/`modelOutput`, not Converse**, so the helper formats the
  **model-native request body** — swapping to another model is no longer a one-line change.
  - `build_recap_record(record_id, highlights) -> dict` returns one batch JSONL line
    `{"recordId", "modelInput"}`, where `modelInput` is the configured model's native InvokeModel body
    (for Llama 3.3 70B: the Llama-3 instruct prompt built from the voice/system text + highlights, plus
    `max_gen_len`/`temperature`).
  - `parse_recap_output(model_output) -> {"headline", "body"}` parses a record's `modelOutput` into a
    headline line + `\n\n`-joined body paragraphs (no markdown).
  - **Voice (system prompt)** unchanged: lighthearted-but-journalistic column, roasts where deserved, a
    single **creative** headline (wit/wordplay hooked to the week's most dramatic real moment; generic
    "Week N recap" / "A beats B" templates banned) then body paragraphs.
  - **Name / fact-fidelity guardrail (required in the prompt)** unchanged: use team and
    manager/display names **exactly as provided**, **never invent real names or facts** (`chris_j`
    stays "Chris"/"chris_j", never "Chris Johnson"); every number, player, and outcome must trace to the
    input. An obvious deduction from the data is allowed.
- **Enqueue — `src/common/recap_queue.py`** (`record_pending_recap(...)`, vendored into webhook +
  processor):
  - Writes an **idempotent** pending marker `PK=RECAP_QUEUE`, `SK=PENDING#{canonical_league_id}` with
    `{platform, native_league_id, correlation_id, trace_context, status="pending", enqueued_at}`. **One
    marker per league** (a re-trigger refreshes it), so the queue never duplicates.
  - A **conditional put that will not clobber an `in_flight` marker** — a league already mid-job stays
    mid-job; its newly-completed weeks are picked up on the next enqueue after that job finishes.
  - No-op when billing is disabled or in the **non-east region** (the `RECAP_*` env unset). A failed put
    is swallowed so enqueue never fails the webhook (still 200) or the processor run.
  - **Replaces** the prior `ecs:RunTask` launch in both triggers.
- **Drainer — `src/recap_drainer/handler.py`** (east-only Lambda; **EventBridge cron**, default every
  15 min):
  - No-op when `is_billing_enabled()` ([BE-017](BE-017-feature-flags.md)) is off.
  - Query all `PK=RECAP_QUEUE` `PENDING#` markers with `status="pending"`.
  - **Per league, premium gate before any spend:** read the `METADATA` item; when the premium feature is
    paywalled (`is_feature_paywalled("premium_feature")`) and the league is **not** active
    (`now >= subscription_end_time`, or absent), **delete the marker and skip** — no records emitted, no
    Bedrock spend. (Mirrors `require_active_subscription`, [BE-014](BE-014-subscription-access-control.md).)
  - **Enumerate all seasons** (GSI1 `LEAGUE_LOOKUP` merge, same as `get_league_seasons`) → completed
    weeks (`MATCHUPS#{season}#` prefix; presence implies completion) → **drop already-recapped weeks**
    (existence check on `MATCHUP_RECAP#{season}#WEEK#{week:02d}`) → **build highlights** per matchup
    (both teams' display name + record + score, winner/margin, each side's top 1–2 starters + top bench,
    playoff round if any; trim PlayerStat detail to keep tokens low) → emit one batch record per missing
    `(season, week)` with `recordId={canonical_league_id}#{season}#W{week:02d}`. Read `STANDINGS#{season}`
    once per season for records/context.
  - **Minimum-job-size handling:** if the total record count across **all** pending leagues is **below**
    Bedrock's minimum records-per-job, submit nothing this tick and **leave the markers** — work
    accumulates until a later tick clears the floor. (Verify the current minimum for the model/region; if
    it is trivially low, every tick submits.)
  - Otherwise: write the input JSONL to `s3://<batch bucket>/input/<job>.jsonl`,
    `CreateModelInvocationJob` (`roleArn` = the Bedrock batch service role; output to
    `s3://<batch bucket>/output/<job>/`), write a **job-manifest** item `PK=RECAP_JOB#{job}`,
    `SK=MANIFEST` mapping each `recordId → (canonical_league_id, season, week)` plus the output prefix,
    and **flip the drained league markers to `status="in_flight"` with the job id** (not delete — see
    failure recovery).
  - **Idempotent:** already-recapped weeks are excluded before records are built, so re-drains never
    regenerate.
  - **Stale-in-flight safety net:** an `in_flight` marker older than a threshold (job vanished / never
    emitted a terminal event) is treated as `pending` and resubmitted.
- **Completion — `src/recap_completion/handler.py`** (east-only Lambda; **EventBridge** rule on
  `aws.bedrock` *Batch Inference Job State Change*):
  - On **`Completed`**: load the manifest by job id, read each output JSONL record from the job's S3
    output prefix, `parse_recap_output` → write the `MATCHUP_RECAP#{season}#WEEK#{week:02d}` item
    `data={headline, body, generated_at, model}` (**idempotent** — skip if already present). Delete the
    manifest and the now-satisfied league markers. Per-record parse/write failures are caught and logged
    so one bad record never drops the rest.
  - On **`Failed`/`Stopped`/`Expired`**: log + **SNS alert** (prod), and **reset the affected leagues'
    markers from `in_flight` back to `pending`** so the next drain resubmits; idempotent skip means only
    still-missing weeks are rebuilt.
- **Tracing ([BE-021](BE-021-async-chain-otel-propagation.md)):** aggregation **breaks single-trace
  continuity**. Each enqueue marker still carries the trigger's `correlation_id` + `trace_context` for
  log correlation, but because the drainer batches many leagues into one job it **roots its own trace**
  (`recap_drainer.handle`) rather than continuing any one trigger's span; the completion handler roots
  `recap_completion.handle`. The processor/webhook → recap **parent-child span linkage is dropped** (a
  consequence of going async + aggregated); per-league `correlation_id` still threads the logs. (Trigger
  trace contexts could be attached as span **links** if needed.) Each Lambda calls `init_tracing(...)` at
  module top level and wraps its run in `traced_handler(...)`; a true no-op when Axiom is unconfigured.
  Requires the `opentelemetry-*` packages (+ `boto3`, `openfeature-sdk`) in each Lambda's
  `requirements.txt`.
- **Triggers (two; now enqueue-only, both premium-deferred + idempotent):**
  - **Trigger A — subscription activation** ([BE-015](BE-015-stripe-billing.md)): the Stripe webhook
    calls `record_pending_recap(...)` when `record_active_subscription(...) == True`. **CI gate
    unchanged:** the enqueue is suppressed when the subscription metadata carries an `integration_test`
    marker (real checkout subscriptions never set it), so CI converges subscription state without Bedrock
    spend or writes to the shared dev league.
  - **Trigger B — processor completion** ([BE-004](BE-004-data-processing-pipeline.md)): the processor
    calls `record_pending_recap(...)` at the end of every onboard/refresh. No-op in the non-east region;
    the **drainer's** premium gate prevents non-premium spend; a failed enqueue is swallowed.
- **Query API:** unchanged — `MATCHUP_RECAP` stays in the `QueryType` enum and `QUERY_TYPE_TO_SK_BASE`
  in `src/api/main.py`; `query_league` already prefix-queries by SK base and gates on league
  membership. Read-path premium gating stays client-side (`SubscriptionGuard`); recaps simply do not
  exist for non-subscribers (or for not-yet-generated weeks).
- **Infra:**
  - **Removed:** the `recap_generator` **ECS Fargate task definition**, the `leagueql-recap-generator`
    **ECR repo** + lifecycle, the recap-generator **task + exec roles**, the `ecs:RunTask` /
    `iam:PassRole` / `RECAP_TASK_*` grants + env on the **webhook & processor**, the ECS **task-failed**
    EventBridge rule, and the **ECR image build** in `.github/workflows/build.yaml`.
  - **Added:**
    - **S3 batch bucket** `leagueql-recap-batch-<env>` with `input/` + `output/` prefixes and a
      **lifecycle expiry** (e.g. 7 days) on both.
    - **Bedrock batch service role** (trust `bedrock.amazonaws.com`) with S3 get/put on the batch bucket;
      passed as `roleArn` to `CreateModelInvocationJob`.
    - **Drainer Lambda** `recap_drainer` (east-only) + an EventBridge **cron** rule (default rate 15 min)
      + role: DynamoDB read/write + GSI1, S3 read/write on the batch bucket,
      `bedrock:CreateModelInvocationJob`/`GetModelInvocationJob`/`ListModelInvocationJobs`,
      `iam:PassRole` on the batch service role, `aws-marketplace:Subscribe`/`ViewSubscriptions` (first-run
      self-subscribe), feature-flag + Axiom SSM read.
    - **Completion Lambda** `recap_completion` (east-only) + an EventBridge rule on `aws.bedrock`
      detail-type *Batch Inference Job State Change* (`Completed`/`Failed`/`Stopped`/`Expired`) + role:
      DynamoDB read/write, S3 read on the batch bucket, SNS publish (alerts), feature-flag + Axiom SSM
      read.
    - The ECS task-failed alarm is **replaced** by a **drainer/completion Lambda error alarm** plus the
      batch-job-failed branch's SNS alert (prod).
  - Both Lambdas ship via the **Lambda-zip path** in `build.yaml`, not a container image. The webhook +
    processor get the `RECAP_*` env they need for `record_pending_recap` (DynamoDB table; `""`/unset in
    the non-east region) and **drop** the prior ECS grants/env.
  - **Bedrock model access** unchanged: the *Model access* console page is retired — access is an **AWS
    Marketplace subscription**. The drainer role carries `aws-marketplace:Subscribe`/`ViewSubscriptions`
    so its **first run self-subscribes** the account to the Llama 3.3 70B Marketplace product
    (account-wide, one-time; ~2 min to settle, during which submit returns `AccessDeniedException`).
    Alternatively an admin subscribes once via AWS Marketplace and you drop those two actions.

## Edge Cases
- **Non-premium league:** the drainer's premium gate deletes the marker and emits no records → no batch
  spend. (Trigger A only fires on a real activation.)
- **Billing disabled (BE-017):** enqueue no-ops and the drainer no-ops; nothing is generated. Matches the
  read-path behavior where recaps are ungated when billing is off but never generated by these triggers in
  that state.
- **No matchup data for a league/season:** the league contributes zero records; no error.
- **Already-recapped week:** excluded by the existence check before records are built; **never**
  regenerated once written.
- **Below the minimum job size:** the drainer submits nothing and leaves the markers; work accumulates
  across ticks/leagues until the floor clears. To bound a lone league's wait, lower the cron interval (or,
  if the model's minimum is trivially low, every tick submits).
- **Batch job failure (`Failed`/`Stopped`/`Expired`):** the completion handler logs + alerts (prod) and
  **resets the affected leagues' markers to `pending`** so the next drain resubmits; idempotent skip
  rebuilds only still-missing weeks.
- **Stale in-flight marker** (job vanished / no terminal event): a drain treats an `in_flight` marker
  older than the threshold as `pending` and resubmits. The `MATCHUP_RECAP` write is idempotent, so at
  worst a week is generated twice (wasted spend, no corruption).
- **New weeks while a job is in flight:** enqueue's conditional put won't clobber an `in_flight` marker,
  so the league isn't re-drained for its in-flight weeks; newly-completed weeks are picked up on the next
  enqueue after that job finishes (slight extra latency, no double spend).
- **One bad output record:** caught and logged; every other record in the same job is still written.
- **Enqueue failure:** swallowed — never fails the webhook (still 200) or the processor run; the next
  trigger re-enqueues.
- **Latency:** end-to-end = drain interval + batch turnaround; **no recap is immediate**, including for a
  just-subscribed league. FE-037 shows a generating state for weeks with no item yet. Batch has no SLA;
  under contention turnaround can stretch to hours.
- **Tracing unconfigured:** `init_tracing`/`traced_handler` are no-ops; each stage runs untraced with
  `correlation_id`-only logging. An Axiom export error never changes the outcome.

## Acceptance Criteria
- [ ] For a **multi-season premium** league, after **enqueue → drain → batch completion**, a
      `MATCHUP_RECAP#{season}#WEEK#{week}` item exists for **every** completed week of **every** season,
      each with a non-empty `headline` and `body` plus `generated_at` and `model`.
- [ ] A second full cycle for the same league is a **no-op** (no new records submitted, no item changes).
- [ ] A **non-premium** league (paywalled + no active subscription) produces **no** records and incurs
      **no** batch-job spend — the drainer's gate deletes its marker.
- [ ] With billing disabled, both enqueue and the drainer no-op immediately.
- [ ] When pending work is **below** the batch minimum, the drainer submits nothing and **retains** the
      markers; a later tick that clears the floor submits **one** job covering the accumulated work.
- [ ] A batch-job failure **resets** the affected leagues to `pending` and the next drain resubmits; one
      bad output record does not drop the others.
- [ ] The Stripe webhook enqueues **only** when `record_active_subscription` returns `True`; a
      stale/duplicate event does not; the `integration_test` marker suppresses enqueue.
- [ ] The processor enqueues at the end of every onboard/refresh; a failed enqueue does not fail the
      processor run.
- [ ] `GET /leagues/{leagueId}/query?queryType=MATCHUP_RECAP#{season}#WEEK#{week}` returns the cached
      recap for members and 404s for a week not yet generated.
- [ ] Recaps use team/manager names exactly as provided and contain no fabricated names, stats, or events
      not present in the highlights.
- [ ] The ECS recap task, its ECR repo/image build, and the `RunTask`/`RECAP_TASK_*` grants are
      **removed**; generation runs entirely through the **drainer + completion Lambdas**.

## Sources
`src/common/bedrock.py`, `src/common/recap_queue.py`, `src/recap_drainer/handler.py`,
`src/recap_completion/handler.py`, `src/recap_drainer/requirements.txt`,
`src/recap_completion/requirements.txt`, `src/stripe_webhook/handler.py`, `src/processor/handler.py`,
`src/api/main.py`, `src/common/subscription.py`, `src/common/feature_flags.py`,
`src/common/tracing.py`, `infrastructure/regional/main.tf`, `infrastructure/global/{dev,prod}/main.tf`,
`.github/workflows/build.yaml`, `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md`.
