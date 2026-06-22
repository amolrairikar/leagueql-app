# BE-022: Weekly Recap Generator

## Description
Generates a narrative "commissioner's column" for each historical week of a premium league —
storylines, upsets, standout performances, and light trash talk — from data LeagueQL has
already computed. The recap is composed **deterministically** by assembling a curated bank of
phrase/snippet templates (no LLM). It is a **premium-only** feature triggered by an event
**outside** the onboard/refresh request path: a genuine premium activation in the
Stripe billing webhook ([BE-015](BE-015-stripe-billing.md)) fans out an asynchronous backfill
that generates a recap for **every season/week** the league has matchups for. The generator is
**idempotent** per week, so re-firing (Stripe's at-least-once delivery, renewals,
partial-completion retries, re-upgrades) is safe and never duplicates work.

It runs as a dedicated async Lambda (`src/recap/`) mirroring the existing async workers
(`sleeper_refresh`, `processor`). (Premium gating + the Stripe-webhook trigger are kept from
the feature's original LLM-backed design even though deterministic composition is free to run.)

### Trigger
- `src/stripe_webhook/handler.py` captures the return of `record_active_subscription`. When it
  returns `True` (a genuine, monotonic apply) **and** the subscription status is
  `active`/`trialing`, the webhook async-invokes the recap Lambda
  (`InvocationType="Event"`) with `{canonical_league_id, correlation_id, trace_context}`.
- The webhook remains the **single writer** of subscription state; recap generation is a
  downstream, idempotent consumer. The invoke is fire-and-forget — a recap failure never
  affects subscription convergence.

### Inputs — deterministic highlights (facts in code, prose out)
The composer consumes **pre-computed deterministic highlights**, never raw box scores or bare
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

All numbers in the recap originate here, so the prose can only ever restate facts the composer
was handed. Playoff stakes are framed only for matchups actually flagged as playoff games.

### Recap composition (deterministic snippet templates)
- **No LLM, no provider, no network, no secret.** `generate.py` (`generate_recap`) assembles
  the recap from a curated phrase bank (`snippets.py`) — there is no Bedrock call, model id, or
  API key.
- **Selection is seeded.** Each matchup's sentences are drawn with a `random.Random` seeded
  from a stable `hashlib.sha256` of that matchup's own facts (season, week, index, both
  managers, both scores, margin). So the same week always renders the **same** recap (stable on
  idempotent re-fire) while different matchups and weeks read differently, and the output is
  fully reproducible / testable.
- **Structure.** The body is **one short paragraph (2-3 sentences) per matchup**, covering every
  matchup in the data in order, separated by blank lines. Per paragraph: a result sentence
  chosen by margin bucket (tie / nailbiter / close / solid / comfortable / blowout) or a playoff
  override (advance / championship), a standout-performance sentence for the week's higher top
  scorer, an optional flavor sentence (biggest-bust, bench-points regret, trash talk, or
  postseason elimination), and a week-extreme tag on the biggest / closest decided game. A
  headline is chosen from a set keyed to the week's shape (championship > playoff > blowout >
  general). It returns `{headline, body}`.
- The snippet bank's generator version is recorded in each recap's `model` field
  (e.g. `snippet-v1`) so a recap can be traced to the composer that wrote it. `generate_recap`
  raises `RecapGenerationError` only as a defensive guard (a week with no matchups); composition
  otherwise always succeeds.

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
   Composition is in-memory and instant (no LLM), so the backfill runs single-threaded;
   the only per-week DynamoDB call in this step is the `put_item`.
6. Track progress via a `JOB_STATUS` item ([BE-008](BE-008-job-status-tracking.md)) keyed by
   `correlation_id`: `COMPLETED` when the run finishes, `FAILED` (failure_code `RECAP`) when a
   week's generation raised. Best-effort, never raises.

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
- **A week raises during composition (defensive):** composition is deterministic and effectively
  always succeeds, but if `generate_recap` raised, that week is skipped (no item written), the run
  is marked `FAILED` with failure_code `RECAP`, and the alarmable error path fires; other weeks
  still succeed and a later retry fills the gap.
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
- [ ] All facts in a recap come from `compute_highlights`; `generate_recap` composes the prose
      deterministically from `snippets.py` with no LLM/network call, and the same week always
      renders the same recap.
- [ ] The run records `JOB_STATUS` `COMPLETED` on success and `FAILED` (failure_code `RECAP`) when
      a week's generation fails; JOB_STATUS writes never raise.
- [ ] `RECAP` is queryable through the BE-005 endpoint (both `RECAP#{season}#WEEK#{WW}` and the
      bare-prefix `RECAP#{season}#` season read).

## Sources
`src/recap/handler.py`, `src/recap/highlights.py`, `src/recap/generate.py`,
`src/recap/snippets.py`, `src/stripe_webhook/handler.py`, `src/common/onboarder_invoke.py`,
`src/api/main.py`
(`QueryType` / `QUERY_TYPE_TO_SK_BASE`), `src/common/job_status.py`,
`src/common/feature_flags.py`, `src/common/tracing.py`.
