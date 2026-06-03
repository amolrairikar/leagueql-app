# BE-015: Stripe Billing — Checkout, Webhook & Subscription Lifecycle

## Description
Establishes and maintains each league's paid subscription through **Stripe**, making the
`subscription_end_time` consumed by [BE-014](BE-014-subscription-access-control.md) an
**authoritative, server-derived** value rather than a client-supplied one. The model is
**per league**:

- **One Stripe Customer per Clerk user** — a single card/payer that can hold many
  subscriptions.
- **One Stripe Subscription per league** — each has its own independent trial clock and
  billing cycle. The subscription carries `metadata.canonical_league_id` so webhook events
  route back to the correct league.

A **Stripe webhook is the single writer** of `subscription_end_time` (= `trial_end` while
`status: trialing`, then `current_period_end` once paying). Access enforcement stays live
and per-request in BE-014 — this feature introduces **no scheduled job or polling**, only an
event-driven webhook.

## Scope
- **Checkout endpoint** (Clerk-authed): `POST /leagues/{id}/checkout-session` — resolves or
  creates the user's Stripe Customer, claims a synchronous `pending_checkout` marker on the
  league `METADATA` (conditional write — see Idempotency Layer 1), creates a Stripe Checkout
  Session in `subscription` mode with `subscription_data.metadata.canonical_league_id` and
  `subscription_data.trial_period_days` (included only when the league has no `trial_used`
  marker — see the trial edge case), and returns the session URL. Returns `409` when the
  league already has an active subscription or an unexpired in-flight checkout.
- **Webhook endpoint / Lambda** (no Clerk auth; `Stripe-Signature` verified): `POST
  /stripe/webhook` — on `checkout.session.completed`,
  `customer.subscription.created|updated`, and `invoice.paid`, calls
  `update_subscription_end_time(canonical_league_id, trial_end | current_period_end)`; on
  `customer.subscription.deleted` or terminal payment failure, sets `subscription_end_time`
  to the past (gate flips to expired live).
- **Billing portal endpoint** (Clerk-authed): `POST /billing-portal-session` — returns a
  Stripe Billing Portal URL for the user's Customer (update card / cancel). Cancellation is
  configured to take effect **immediately** (not at period end). Backs the frontend "Manage
  Subscription" dialog ([FE-021](../frontend/FE-021-subscription-access-control.md)).
- **Mapping (planned schema):** `stripe_customer_id` stored once per user (a
  `USER#{clerk_user_id}` item); on the league `METADATA` item — `stripe_subscription_id`,
  `pending_checkout` (in-flight checkout marker `{session_id, expires_at}` with a short TTL,
  cleared by the webhook on success), and `trial_used` (set when the league's first trial is
  granted, never cleared); and `canonical_league_id` in the Stripe subscription metadata. To
  be added to `docs/db/dynamodb_spec.md` when implemented.
- **Secrets & environment mode:** Stripe secret key + webhook signing secret in SSM/Secrets
  Manager, injected to the API and webhook Lambdas (new Terraform). Never committed or logged.
  **DEV uses Stripe sandbox (test) mode and PROD uses live mode** — each environment is
  configured with its own mode-specific credentials (`sk_test_…`/`sk_live_…`, the matching
  `whsec_…` webhook signing secret) and its own mode-specific Price/Product IDs. Test- and
  live-mode objects (Customers, Subscriptions, Prices, webhook endpoints) are fully isolated
  by Stripe, so no resource is shared across environments.
- **Reuses** BE-014's `require_active_subscription` (enforcement) **unchanged**.
  `update_subscription_end_time` remains the sole write path but is **extended** from its
  current unconditional single-attribute `SET` into a **conditional, multi-attribute** update
  (monotonic guard on `subscription_end_time`, conditional claim of `stripe_subscription_id`,
  and clearing of `pending_checkout`) — see Idempotency Layer 3.

## Idempotency
Stripe delivers webhooks **at-least-once** and may **reorder** them, and the checkout
endpoint may be retried. Idempotency is enforced in three layers — *don't duplicate
provisioning/billing*, and *converge to correct state regardless of arrival order*. (Stripe
owns charge-level idempotency; we never create charges directly, so our concern is duplicate
provisioning, not duplicate charging.)

- **Layer 1 — outbound API calls (no duplicate Customers/subscriptions):**
  - Send a Stripe `Idempotency-Key` on every mutating call — keyed by `clerk_user_id` for
    Customer creation, and by the `pending_checkout.session_id` (a per-attempt nonce) for the
    Checkout Session — so a network retry returns the original result. The key is scoped
    per-attempt, **not** by `canonical_league_id` alone: concurrency is handled by the
    `pending_checkout` marker below, and a coarse league-level key (valid ~24h in Stripe)
    would wrongly return a stale session for a legitimate later or re-subscribe checkout.
  - Get-or-create the Customer via the stored `stripe_customer_id` (`USER#{clerk_user_id}`);
    create only when absent. This plus the idempotency key closes the concurrent
    first-checkout race.
  - **Pre-check** that the league has no active `stripe_subscription_id` before opening a
    Checkout Session — the one duplicate that would actually double-bill the user. Because
    `stripe_subscription_id` is written only by the (async, possibly late) webhook, this read
    alone is a stale projection, so the check is reinforced by:
    - **Synchronous `pending_checkout` marker:** claim it with a conditional write —
      `attribute_not_exists(stripe_subscription_id) AND (attribute_not_exists(pending_checkout)
      OR pending_checkout.expires_at < :now)`. DynamoDB serializes concurrent attempts so only
      one wins; the loser gets `409` and creates no session. The `expires_at` TTL lets an
      abandoned checkout self-heal so the league is never permanently blocked.
    - **Authoritative Stripe check (optional belt-and-suspenders):** for the residual window
      where a very late webhook lands after the marker expires, query
      `Subscription.list(customer, status active|trialing)` filtered by
      `metadata.canonical_league_id` and refuse if one already exists — the source of truth,
      not the lagging projection.
- **Layer 2 — inbound webhook dedup (exactly-once application):**
  - Verify `Stripe-Signature` first (reject `400`); no processing on unverified payloads.
  - Dedup on `event.id` with a `WEBHOOK_EVENT#{evt_id}` item (+ TTL), mirroring the existing
    `correlation_id`-keyed item pattern. **Check then process then record:** look the marker up
    first (found → redelivery → ack `200` and skip); otherwise process the event and write the
    marker **only after** processing succeeds. Recording after success (rather than claiming
    the marker up front) avoids a lost update if the handler fails mid-processing — the
    redelivery is then reprocessed, and Layer-3 convergence makes reprocessing safe.
- **Layer 3 — state convergence (handles out-of-order):** the write is the extended,
  conditional `update_subscription_end_time` — a single multi-attribute `UpdateItem` that
  applies the monotonic guard, claims `stripe_subscription_id`, and clears `pending_checkout`.
  - Derive `subscription_end_time` from the subscription's **authoritative current state**
    (refetch via `Subscription.retrieve`) rather than the event payload's delta, so a stale
    event simply re-writes the current value.
  - Guard the write to only **advance** `subscription_end_time` (conditional `:new >
    existing`); a late stale event cannot regress access.
  - **Cancellation is the deliberate exception** to the monotonic rule: a terminal
    `status` (`customer.subscription.deleted` / terminal payment failure) sets the value to
    the past, keyed on event type + status, not a timestamp comparison.
  - **Duplicate-subscription reconciliation (backstop):** the first `customer.subscription.created`
    to arrive claims `stripe_subscription_id` with a **conditional write**
    (`attribute_not_exists(stripe_subscription_id)`), making a single deterministic winner.
    A second `created` for a *different* subscription on the same league fails that condition
    → it recognizes itself as the duplicate and `Subscription.cancel`s **its own** subscription
    (never the recorded winner), so concurrent events cannot cancel each other. The winning
    write clears the `pending_checkout` marker. A duplicate caught during the trial cancels
    before any invoice, so no charge occurs.

## Edge Cases
- **Invalid `Stripe-Signature`:** webhook returns `400` with no state change.
- **Onboarded but never subscribed:** no subscription → `subscription_end_time` absent →
  BE-014 paywalls the league. Onboarding itself stays ungated.
- **Cancellation is immediate:** canceling (via the Billing Portal or API) cancels the Stripe
  subscription **now**, not at period end — `customer.subscription.deleted` fires immediately,
  the webhook sets `subscription_end_time` to the past, and BE-014 revokes access on the next
  request (live evaluation, no job). No remaining-period access is granted.
- **Payment failure / dunning:** access remains until `current_period_end`; a terminal
  failure (subscription deleted) sets `subscription_end_time` to the past.
- **Per-league trial, once only (no reuse):** a league is eligible for the trial **only on
  its first-ever subscription**. Re-subscribing a league that previously had any subscription
  is created with **no trial** (`trial_period_days` omitted). This is enforced by a
  `trial_used` marker on the league `METADATA`, set when the first trial is granted and never
  cleared; checkout omits the trial whenever `trial_used` is present. (Trials remain
  independent *across different* leagues — each league gets its single trial.)
- **One user, many leagues:** a single Customer holds multiple Subscriptions; each webhook
  event routes by `metadata.canonical_league_id` and each league is gated independently.
- **Customer first use / concurrency:** the Clerk user ↔ Stripe Customer mapping is created
  on demand; concurrent first-checkout requests must not create duplicate Customers (look up
  by `clerk_user_id` and/or use a Stripe idempotency key).
- **Late webhook + second checkout (duplicate-subscription race):** a subscription exists in
  Stripe but its `created` webhook is delayed, so `stripe_subscription_id` is not yet on
  `METADATA`. A second checkout attempt in that window must not open a second subscription.
  The synchronous `pending_checkout` marker (Layer 1) blocks the concurrent/short-window case
  with a `409`; the optional Stripe `Subscription.list` check covers the residual late-webhook
  window; and webhook reconciliation (Layer 3) cancels any duplicate that still slips through.
- **Refund / chargeback:** reflected via `customer.subscription.updated|deleted` →
  `subscription_end_time` updated accordingly.
- **Environment mode mismatch:** a live-mode webhook signature cannot be verified with the
  test-mode signing secret (and vice versa), so a misconfigured environment fails closed at
  signature verification (`400`) rather than silently writing state. DEV must never be wired
  with live-mode keys, nor PROD with test-mode keys.

## Acceptance Criteria
- [ ] `POST /leagues/{id}/checkout-session` returns a Stripe Checkout URL for the
      authenticated user, with the league's `canonical_league_id` in the subscription
      metadata and the configured trial applied.
- [ ] After checkout completes, the league `METADATA` `subscription_end_time` equals the
      subscription's `trial_end` (trialing) or `current_period_end` (active), and is written
      **only** by the webhook.
- [ ] `POST /stripe/webhook` rejects an invalid `Stripe-Signature` with `400` and makes no
      state change.
- [ ] `invoice.paid` renewal advances `subscription_end_time` to the new
      `current_period_end`; `customer.subscription.deleted` sets it to the past.
- [ ] Cancellation takes effect immediately: the subscription is canceled now (not at period
      end) and `subscription_end_time` is set to the past, revoking access on the next request.
- [ ] A league's first subscription includes the trial; any subsequent subscription for that
      league (after `trial_used` is set) is created with no trial.
- [ ] Webhook processing is idempotent — duplicate or out-of-order deliveries never regress
      `subscription_end_time`.
- [ ] A single user can hold active subscriptions for multiple leagues simultaneously, each
      gated independently by BE-014.
- [ ] A second checkout attempt for a league with an active subscription **or** an unexpired
      `pending_checkout` marker returns `409` and creates no Stripe Checkout Session.
- [ ] The `pending_checkout` marker is claimed via a conditional write (only one of two
      concurrent attempts wins) and is cleared by the webhook once the subscription is
      recorded; an expired marker no longer blocks a new checkout.
- [ ] If a duplicate subscription is ever created for a league, the webhook reconciles to a
      single active subscription by canceling the extra, leaving exactly one
      `stripe_subscription_id` on `METADATA`.
- [ ] `POST /billing-portal-session` returns a Stripe Billing Portal URL for the user's
      Customer.
- [ ] The client-supplied `subscriptionEndTime` onboarding input is removed;
      `subscription_end_time` is set only server-side via this flow (supersedes the
      [BE-001](BE-001-league-onboarding.md) interim behavior).
- [ ] Stripe secret key and webhook signing secret are sourced from SSM/Secrets Manager and
      never committed or logged.
- [ ] DEV is configured with Stripe sandbox (test) mode credentials and Price IDs; PROD is
      configured with live mode; neither environment carries the other's keys.

## Implementation Notes
- **Extending `update_subscription_end_time` is a breaking change to its current contract.**
  It goes from an unconditional single-attribute `SET subscription_end_time = :s` to a
  conditional, multi-attribute `UpdateItem` (monotonic guard, conditional `stripe_subscription_id`
  claim, `pending_checkout` clear). Its **existing BE-014 unit tests must be updated** to cover
  the new conditional behavior (advance vs. no-op on stale/regressive writes, the
  cancellation/terminal-status exception, and the duplicate-subscription claim race). Update the
  helper, its callers, and its tests together when this lands.

## Sources
*(Planned — not yet implemented.)*
`src/api/routes.py` (checkout + billing-portal endpoints), new Stripe webhook Lambda,
`src/api/helpers.py` (`update_subscription_end_time` — extended to a conditional,
multi-attribute write; `require_active_subscription` — reused unchanged), `infrastructure/`
(Stripe secrets, webhook route/Lambda),
`docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md` (planned `stripe_subscription_id`,
`pending_checkout`, and `trial_used` on METADATA, `USER` item with `stripe_customer_id`,
`WEBHOOK_EVENT` dedup item),
[BE-014](BE-014-subscription-access-control.md), [BE-001](BE-001-league-onboarding.md).
