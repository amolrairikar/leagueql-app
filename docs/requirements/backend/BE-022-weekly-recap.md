# BE-022: Weekly Recap Generator

## Description
Generates a narrative "commissioner's column" for each historical week of a premium league —
storylines, upsets, standout performances, and light trash talk — from data LeagueQL has
already computed. The recap reads as a **sports-newspaper-style column**, not a list of
per-matchup blurbs: an LLM (**Amazon Nova Premier** on Amazon Bedrock) is the author and decides
the article's lede, structure, ordering, and emphasis. Two things keep it honest: (1) the model
is handed only the **pre-computed deterministic highlights** and writes at **temperature 0**
against a hard guardrail to use only those numbers and names; (2) a **numeric-validation gate**
rejects any recap that prints a number the facts didn't contain. There is **no deterministic
fallback** — if the model fails, is blocked, or produces an unfaithful recap, that week is left
un-recapped and a later retry regenerates it. It is a **premium-only** feature triggered by an
event **outside** the onboard/refresh request path: a genuine premium activation in the Stripe
billing webhook ([BE-015](BE-015-stripe-billing.md)) fans out an asynchronous backfill that
generates a recap for **every season/week** the league has matchups for. The generator is
**idempotent** per week, so re-firing (Stripe's at-least-once delivery, renewals,
partial-completion retries, re-upgrades) is safe and never duplicates work.

It runs as a dedicated async Lambda (`src/recap/`) mirroring the existing async workers
(`sleeper_refresh`, `processor`). Authentication to Bedrock is the Lambda's IAM execution role
(SigV4) — there is **no API-key secret**.

### Trigger
- `src/stripe_webhook/handler.py` captures the return of `record_active_subscription`. When it
  returns `True` (a genuine, monotonic apply) **and** the subscription status is
  `active`/`trialing`, the webhook async-invokes the recap Lambda
  (`InvocationType="Event"`) with `{canonical_league_id, correlation_id, trace_context}`.
- The webhook remains the **single writer** of subscription state; recap generation is a
  downstream, idempotent consumer. The invoke is fire-and-forget — a recap failure never
  affects subscription convergence.

### Inputs — deterministic highlights (facts in code, prose out)
The pipeline consumes **pre-computed deterministic highlights**, never raw box scores or bare
scores. `highlights.py` (`compute_highlights`) is a pure function over a week's `MATCHUPS` rows
plus the season's `WEEKLY_STANDINGS` snapshot for that week. Per matchup it emits a compact
dict:
- final score + winner/loser team names,
- top scorer per team (name / position / points),
- biggest bust per team (lowest-scoring starter),
- points left on the bench (sum of bench `points_scored` — best-legal-swap analysis is out of
  scope),
- the week's closest and biggest margins,
- playoff context per matchup (`is_playoff`, `playoff_tier_type`, `playoff_round`) plus a
  week-level `is_playoff_week` flag, so the recap can frame postseason stakes — celebrating a
  winner advancing / being crowned champion and calling out the losing team's elimination,
- standings movement for the week (from `WEEKLY_STANDINGS#{season}` filtered to the matching
  `snapshot_week`).

All numbers in the recap originate here, so the prose can only ever restate facts the pipeline
was handed. Playoff stakes are framed only for matchups actually flagged as playoff games.

### Recap composition (AI column → validate)
The orchestrator `compose.py` (`generate_recap`) runs two steps; `handler.py` imports it and is
agnostic to how the prose is produced.

1. **AI prose (`ai_generate.py`, Amazon Bedrock Converse).** `bedrock-runtime.converse` is called
   with **Amazon Nova Premier** at **temperature 0**. The system prompt frames the recap as a
   **sports-newspaper-style column** in the existing lively, opinionated commissioner voice (a
   lede, then a flowing multi-paragraph article — the model decides which stories lead), with the
   output contract (`{headline, body}`) and a **hard guardrail**: use ONLY the numbers/names in
   the supplied data; never invent or alter a score, player, or record, and frame playoff stakes
   only for matchups the data marks as playoff games. The user turn carries the `highlights` JSON
   (the model's only source of facts). Model id is `BEDROCK_MODEL_ID`
   (default `us.amazon.nova-premier-v1:0`, the cross-region inference profile), env-overridable per
   region. Content-filter / guardrail interventions surface as a Converse `stopReason`
   (`content_filtered` / `guardrail_intervened`) and are treated as a failure
   (`RecapGenerationError`), as are empty / unparseable responses.
2. **Numeric-validation gate (`validate.py`, `validate_recap`).** Every numeric token in the
   generated `headline + body` must match a fact from `highlights` (scores, margins, points,
   ranks, records) within a small rounding tolerance. A recap that prints a number the facts don't
   contain is rejected (`RecapGenerationError`).

There is **no fallback**: `compose.generate_recap` raises `RecapGenerationError` when the week has
no matchups, the model fails / is blocked, or validation rejects the output. `handler.py` records
that week as failed (failure_code `RECAP`) and a later retry regenerates it.

- The recap's `model` field records the Bedrock model id that produced it
  (e.g. `us.amazon.nova-premier-v1:0`), so a recap can be traced to its source.

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
5. For each missing week: `compute_highlights` → `generate_recap` (Bedrock → validate) →
   `put_item` the `RECAP`. All DynamoDB **reads** are done up front (idempotency checks +
   standings cache), so the per-week generate+write step — network-bound on the Bedrock call — is
   parallelized with a small bounded thread pool; the only per-week DynamoDB call in this step is
   the `put_item`. A week whose generation raises is left un-recapped (no item written).
6. Track progress via a `JOB_STATUS` item ([BE-008](BE-008-job-status-tracking.md)) keyed by
   `correlation_id`: `COMPLETED` when every week succeeded, `FAILED` (failure_code `RECAP`) when
   any week's generation raised (the un-recapped weeks fill on a later retry). Best-effort, never
   raises.

### OTel tracing (BE-021)
At module load it calls `init_tracing("leagueql-recap")`, and the handler body is wrapped in
`traced_handler("recap", carrier=event.get("trace_context"))` so the Lambda **continues** the
trace the webhook started. A no-op when Axiom is unconfigured.

## Edge Cases
- **No matchups yet:** the week enumeration is empty → nothing generated, run marked
  `COMPLETED`.
- **Partial completion + retry:** a week that raised leaves no `RECAP` item; a subsequent
  invoke (renewal/redelivery/manual) regenerates only the missing weeks (idempotent skip of the
  ones already written).
- **Re-upgrade after expiry:** every week is already recapped → all skipped → no rework.
- **Subscription canceled before processing:** the METADATA re-check fails and nothing is
  generated.
- **Billing/premium flag off:** the feature-flag gate short-circuits with no generation.
- **Bedrock fails, is blocked, or returns an invalid recap:** the AI step raises (transient error,
  `content_filtered` / `guardrail_intervened`, empty / unparseable) or the validation gate rejects an
  unfaithful recap. There is no fallback — that week is skipped (no item written), the run is marked
  `FAILED` with failure_code `RECAP`, the alarmable error path fires, and a later retry regenerates
  it; other weeks still succeed.
- **Stale/duplicate webhook delivery:** `record_active_subscription` returns `False` on a
  non-advancing write, so no invoke is fired; a genuine apply that *is* redelivered re-invokes
  but finds all weeks already recapped.

## Acceptance Criteria
- [ ] A genuine `record_active_subscription` apply with an active/trialing status async-invokes
      the recap Lambda with `canonical_league_id`, a fresh `correlation_id`, and the webhook's
      `trace_context`; a non-advancing (`False`) write does not.
- [ ] The recap Lambda generates exactly one `RECAP#{season}#WEEK#{WW}` item per league
      season/week that has `MATCHUPS`, skipping any that already exist.
- [ ] A re-invocation after a complete backfill writes nothing new (idempotent).
- [ ] Generation is skipped entirely when `premium_feature` is not paywalled or the league's
      `subscription_end_time` is not in the future.
- [ ] All facts in a recap come from `compute_highlights`; the AI writes from those facts under a
      hard numeric guardrail, and the numeric-validation gate rejects any recap that prints a number
      not present in the highlights.
- [ ] On any Bedrock failure (blocked / empty / unparseable) or a failed validation, no `RECAP` item
      is written for that week and it is regenerated on a later retry (there is no fallback).
- [ ] Each recap's `model` field records the Bedrock model id that produced it.
- [ ] The run records `JOB_STATUS` `COMPLETED` when every week succeeded and `FAILED` (failure_code
      `RECAP`) when any week's generation fails; JOB_STATUS writes never raise.
- [ ] `RECAP` is queryable through the BE-005 endpoint (both `RECAP#{season}#WEEK#{WW}` and the
      bare-prefix `RECAP#{season}#` season read).

## Sources
`src/recap/handler.py`, `src/recap/highlights.py`,
`src/recap/ai_generate.py`, `src/recap/validate.py`, `src/recap/compose.py`,
`src/stripe_webhook/handler.py`,
`src/common/onboarder_invoke.py`, `src/api/main.py`
(`QueryType` / `QUERY_TYPE_TO_SK_BASE`), `src/common/job_status.py`,
`src/common/feature_flags.py`, `src/common/tracing.py`,
`infrastructure/regional/main.tf` (`BEDROCK_MODEL_ID`),
`infrastructure/global/{prod,dev}/main.tf` (`recap-lambda-role` Bedrock grant).
