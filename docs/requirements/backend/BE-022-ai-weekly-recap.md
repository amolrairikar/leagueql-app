# BE-022: AI Weekly Recap Generator

## Description
Generates an LLM-written narrative "commissioner's column" for each historical week of a
premium league — storylines, upsets, awards, and light trash talk — from data LeagueQL has
already computed. Recaps cost money to generate, so generation is **premium-only** and is
triggered by an event **outside** the onboard/refresh request path: a genuine premium
activation in the Stripe billing webhook ([BE-015](BE-015-stripe-billing.md)) fans out an
asynchronous backfill that generates a recap for **every season/week** the league has matchups
for. The generator is **idempotent** per week, so re-firing (Stripe's at-least-once delivery,
renewals, partial-completion retries, re-upgrades) is safe and never double-spends.

The recap is the first LLM integration in the codebase. It runs as a dedicated async Lambda
(`src/ai_recap/`) mirroring the existing async workers (`sleeper_refresh`, `processor`).

### Trigger
- `src/stripe_webhook/handler.py` captures the return of `record_active_subscription`. When it
  returns `True` (a genuine, monotonic apply) **and** the subscription status is
  `active`/`trialing`, the webhook async-invokes the recap Lambda
  (`InvocationType="Event"`) with `{canonical_league_id, correlation_id, trace_context}`.
- The webhook remains the **single writer** of subscription state; recap generation is a
  downstream, idempotent consumer. The invoke is fire-and-forget — a recap failure never
  affects subscription convergence.

### Inputs — deterministic highlights (facts in code, prose out)
The prompt is fed **pre-computed deterministic highlights**, never raw box scores or bare
scores. This prevents number hallucination and controls token cost. `highlights.py`
(`compute_highlights`) is a pure function over a week's `MATCHUPS` rows plus the season's
`WEEKLY_STANDINGS` snapshot for that week. Per matchup it emits a compact dict:
- final score + winner/loser team names,
- top scorer per team (name / position / points),
- biggest bust per team (lowest-scoring starter),
- points left on the bench (sum of bench `points_scored` — best-legal-swap analysis is out of
  scope),
- the week's closest and biggest margins,
- standings movement for the week (from `WEEKLY_STANDINGS#{season}` filtered to the matching
  `snapshot_week`).

All numbers in the recap originate here; the model is instructed to use only the numbers it is
given.

### Model + provider
- **Model:** Amazon Nova Lite — cheap enough for bulk historical backfill.
- **Provider:** Amazon Bedrock, called through the boto3 `bedrock-runtime` **Converse** API
  (no SDK dependency beyond boto3). The Lambda authenticates to Bedrock via its **IAM execution
  role** (SigV4), so there is **no API-key secret** to store, populate, rotate, or leak —
  Bedrock access is a single `bedrock:InvokeModel` statement on the role. The model id /
  inference-profile id is supplied via the `BEDROCK_MODEL_ID` env var so a region-specific
  inference profile (e.g. `us.amazon.nova-lite-v1:0`) can be set without a code change.
- `generate.py` (`generate_recap`) is the only LLM-touching code. The **system prompt** carries
  persona + voice + output contract + the guardrail ("use only the numbers provided; never
  invent stats"); the **user message** carries the deterministic highlights JSON. It returns
  `{headline, body}`. A blocking `stopReason` (`content_filtered` / `guardrail_intervened`),
  unparseable output, or any API error raises, so that week is left un-recapped and a later
  retry fills it.

### Storage / serving
- One `RECAP#{season}#WEEK#{WW}` item per league/season/week (mirrors `MATCHUPS` keying), PK
  `LEAGUE#{canonical_league_id}`, `data = {season, week, headline, body, model, generated_at}`.
  See [`dynamodb_spec.md`](../../db/dynamodb_spec.md).
- Served through the existing BE-005 query endpoint — `RECAP` is added to the `queryType` enum
  and SK map; no route change. Reads stay member/subscription-gated like every other view.

### Handler steps (`lambda_handler`)
1. **Feature-flag gate:** skip unless `is_feature_paywalled("premium_feature")`.
2. **Active-subscription re-check:** read METADATA; skip if `subscription_end_time` is not in
   the future (an upgrade canceled before processing must not generate).
3. **Enumerate weeks:** paginated DynamoDB `query` on PK `LEAGUE#{cid}`,
   `begins_with(SK, "MATCHUPS#")`.
4. **Idempotency:** for each week, `get_item` on `RECAP#{season}#WEEK#{WW}`; skip if present.
5. For each missing week: `compute_highlights` → `generate_recap` → `put_item` the `RECAP`.
   DynamoDB reads (week enumeration, idempotency checks, standings) are done up
   front single-threaded; the `generate_recap` → `put_item` step then runs across a
   **bounded thread pool** (`RECAP_MAX_CONCURRENCY`, default 4) to keep the
   historical backfill within the Lambda timeout. Concurrency is deliberately small
   so Bedrock's per-account requests/tokens-per-minute quotas are respected (the
   Bedrock client's retry/backoff absorbs the occasional throttle).
6. Track progress via a `JOB_STATUS` item ([BE-008](BE-008-job-status-tracking.md)) keyed by
   `correlation_id`: `COMPLETED` when the run finishes, `FAILED` (failure_code `RECAP`) when a
   week's generation raised. Best-effort, never raises.

### OTel tracing (BE-021)
At module load it calls `init_tracing("leagueql-ai-recap")`, and the handler body is wrapped in
`traced_handler("ai_recap", carrier=event.get("trace_context"))` so the Lambda **continues** the
trace the webhook started. A no-op when Axiom is unconfigured.

## Edge Cases
- **No matchups yet:** the week enumeration is empty → nothing generated, run marked
  `COMPLETED`.
- **Partial completion + retry:** a week that raised leaves no `RECAP` item; a subsequent
  invoke (renewal/redelivery/manual) regenerates only the missing weeks (idempotent skip of the
  ones already written).
- **Re-upgrade after expiry:** every week is already recapped → all skipped → no double-spend.
- **Subscription canceled before processing:** the METADATA re-check fails and nothing is
  generated.
- **Billing/premium flag off:** the feature-flag gate short-circuits with no generation.
- **LLM content-filter / API error on a week:** that week is skipped (no item written), the run
  is marked `FAILED` with failure_code `RECAP`, and the alarmable error path fires; other weeks
  still succeed.
- **Stale/duplicate webhook delivery:** `record_active_subscription` returns `False` on a
  non-advancing write, so no invoke is fired; a genuine apply that *is* redelivered re-invokes
  but finds all weeks already recapped.

## Acceptance Criteria
- [ ] A genuine `record_active_subscription` apply with an active/trialing status async-invokes
      the recap Lambda with `canonical_league_id`, a fresh `correlation_id`, and the webhook's
      `trace_context`; a non-advancing (`False`) write does not.
- [ ] The recap Lambda generates exactly one `RECAP#{season}#WEEK#{WW}` item per league
      season/week that has `MATCHUPS`, skipping any that already exist.
- [ ] A re-invocation after a complete backfill writes nothing new (idempotent, no double-spend).
- [ ] Generation is skipped entirely when `premium_feature` is not paywalled or the league's
      `subscription_end_time` is not in the future.
- [ ] All numeric facts in a recap come from `compute_highlights`; `generate_recap` is the only
      code that calls Bedrock, and a content-filter/API error raises so the week is left un-recapped.
- [ ] The run records `JOB_STATUS` `COMPLETED` on success and `FAILED` (failure_code `RECAP`) when
      a week's generation fails; JOB_STATUS writes never raise.
- [ ] `RECAP` is queryable through the BE-005 endpoint (both `RECAP#{season}#WEEK#{WW}` and the
      bare-prefix `RECAP#{season}#` season read).

## Sources
`src/ai_recap/handler.py`, `src/ai_recap/highlights.py`, `src/ai_recap/generate.py`,
`src/stripe_webhook/handler.py`, `src/common/onboarder_invoke.py`, `src/api/main.py`
(`QueryType` / `QUERY_TYPE_TO_SK_BASE`), `src/common/job_status.py`,
`src/common/feature_flags.py`, `src/common/tracing.py`.
