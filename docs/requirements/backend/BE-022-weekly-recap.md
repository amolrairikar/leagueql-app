# BE-022: Weekly Recap Generator

## Description
Generates a narrative "commissioner's column" for each historical week of a premium league —
storylines, upsets, standout performances, and light trash talk — from data LeagueQL has
already computed. The recap reads as a **cohesive column**, not a list of per-matchup blurbs:
an LLM (**Amazon Nova Premier** on Amazon Bedrock) writes the prose, but it is tightly
constrained so the output stays accurate and consistently structured. Three things keep it
controlled: (1) a **deterministic story outline** built in code from the facts drives the
structure, ordering, and emphasis; (2) the model writes at **temperature 0** against a hard
guardrail to use only the supplied numbers; (3) a **numeric-validation gate** rejects any recap
that prints a number the facts didn't contain, and a **deterministic snippet fallback** (the
phrase-bank composer) guarantees a recap always exists. It is a **premium-only** feature
triggered by an event **outside** the onboard/refresh request path: a genuine premium activation
in the Stripe billing webhook ([BE-015](BE-015-stripe-billing.md)) fans out an asynchronous
backfill that generates a recap for **every season/week** the league has matchups for. The
generator is **idempotent** per week, so re-firing (Stripe's at-least-once delivery, renewals,
partial-completion retries, re-upgrades) is safe and never duplicates work. Because a week is
written once and then skipped, byte-exact cross-run reproducibility is not required; determinism
here means controlled structure, factual accuracy, and guaranteed existence.

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

### Recap composition (deterministic outline → AI column → validate → snippet fallback)
The orchestrator `compose.py` (`generate_recap`) runs four steps; `handler.py` imports it and is
agnostic to how the prose is produced.

1. **Deterministic outline (`outline.py`, `build_outline`).** A pure function turns the highlights
   into an ordered, labeled story plan — no prose. It picks the week's headline angle
   (championship > playoff > blowout > general), orders matchups by significance (the week's
   biggest and closest decided games first), and surfaces the standout performer, the biggest
   blowout, the closest game, and playoff stakes. The outline is what makes the column cohesive
   **and** consistently structured across runs.
2. **AI prose (`ai_generate.py`, Amazon Bedrock Converse).** `bedrock-runtime.converse` is called
   with **Amazon Nova Premier** at **temperature 0**. The system prompt carries the
   commissioner-column persona, the output contract (`{headline, body}`), and a **hard guardrail**:
   use ONLY the numbers/names in the supplied data; never invent or alter a score, player, or
   record. The user turn carries the `highlights` JSON **and** the `outline` (write the column in
   this order, hit these beats). Model id is `BEDROCK_MODEL_ID`
   (default `us.amazon.nova-premier-v1:0`, the cross-region inference profile), env-overridable per
   region. Content-filter / guardrail interventions surface as a Converse `stopReason`
   (`content_filtered` / `guardrail_intervened`) and are treated as a failure
   (`RecapGenerationError`), as are empty / unparseable responses.
3. **Numeric-validation gate (`validate.py`, `validate_recap`).** Every numeric token in the
   generated `headline + body` must match a fact from `highlights` (scores, margins, points,
   ranks, records) within a small rounding tolerance. A recap that prints a number the facts don't
   contain is rejected.
4. **Deterministic snippet fallback (`generate.py` + `snippets.py`).** On any AI failure (blocked /
   empty / unparseable) **or** a failed validation, the orchestrator falls back to the
   phrase-bank composer — the prior deterministic design, retained unchanged. It assembles **one
   short paragraph (2-3 sentences) per matchup** with per-matchup seeded `random.Random`
   (stable `hashlib.sha256` of that matchup's facts), so the fallback is itself fully reproducible.
   This guarantees a recap always exists; `generate_recap` (snippet) raises `RecapGenerationError`
   only as a defensive guard (a week with no matchups).

- **Title framing is gated on the bracket tier**, not just on "is this a playoff game". Only the
  `WINNERS_BRACKET` tier earns advance / championship framing and the elimination angle; the
  `Finals` round within it is the championship. Every other non-`NONE` tier —
  `WINNERS_CONSOLATION_LADDER` (3rd/5th-place games) and `LOSERS_BRACKET` — is a **consolation**
  game framed for pride only, never as a title run or an elimination. A week with **no**
  `WINNERS_BRACKET` game gets a regular (general / blowout) headline, not a playoff one. This holds
  in both the outline (which drives the AI) and the snippet fallback.
- The generator that actually produced a recap is recorded in its `model` field — the Bedrock model
  id (e.g. `us.amazon.nova-premier-v1:0`) for an AI recap, or `snippet-v1` for a fallback — so a
  recap can be traced to its source.

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
5. For each missing week: `compute_highlights` → `generate_recap` (outline → Bedrock → validate →
   snippet fallback) → `put_item` the `RECAP`. All DynamoDB **reads** are done up front
   (idempotency checks + standings cache), so the per-week generate+write step — now network-bound
   on the Bedrock call — is parallelized with a small bounded thread pool; the only per-week
   DynamoDB call in this step is the `put_item`.
6. Track progress via a `JOB_STATUS` item ([BE-008](BE-008-job-status-tracking.md)) keyed by
   `correlation_id`: `COMPLETED` when the run finishes, `FAILED` (failure_code `RECAP`) when a
   week produced nothing (the snippet fallback makes this effectively unreachable). Best-effort,
   never raises.

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
- **Bedrock fails, is blocked, or returns an invalid recap:** the AI step raises / the validation
  gate rejects, and the orchestrator falls back to the deterministic snippet composer, which always
  succeeds — the week still gets a `RECAP` item (with `model: snippet-v1`) and the run stays
  `COMPLETED`.
- **A week raises even in the fallback (defensive):** the snippet composer is deterministic and
  effectively always succeeds, but if it too raised (a week with no matchups), that week is skipped
  (no item written), the run is marked `FAILED` with failure_code `RECAP`, the alarmable error path
  fires, and a later retry fills the gap; other weeks still succeed.
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
- [ ] All facts in a recap come from `compute_highlights`; the AI prose is constrained by a
      deterministic outline and a hard numeric guardrail, and the numeric-validation gate rejects any
      recap that prints a number not present in the highlights.
- [ ] On any Bedrock failure (blocked / empty / unparseable) or a failed validation, the recap falls
      back to the deterministic snippet composer (`model: snippet-v1`) so a `RECAP` item is still
      written and the run stays `COMPLETED`.
- [ ] Each recap's `model` field records the generator that produced it (the Bedrock model id for an
      AI recap, `snippet-v1` for a fallback).
- [ ] The run records `JOB_STATUS` `COMPLETED` on success and `FAILED` (failure_code `RECAP`) when
      a week's generation fails; JOB_STATUS writes never raise.
- [ ] `RECAP` is queryable through the BE-005 endpoint (both `RECAP#{season}#WEEK#{WW}` and the
      bare-prefix `RECAP#{season}#` season read).

## Sources
`src/recap/handler.py`, `src/recap/highlights.py`, `src/recap/outline.py`,
`src/recap/ai_generate.py`, `src/recap/validate.py`, `src/recap/compose.py`,
`src/recap/generate.py`, `src/recap/snippets.py`, `src/stripe_webhook/handler.py`,
`src/common/onboarder_invoke.py`, `src/api/main.py`
(`QueryType` / `QUERY_TYPE_TO_SK_BASE`), `src/common/job_status.py`,
`src/common/feature_flags.py`, `src/common/tracing.py`,
`infrastructure/regional/main.tf` (`BEDROCK_MODEL_ID`),
`infrastructure/global/{prod,dev}/main.tf` (`recap-lambda-role` Bedrock grant).
