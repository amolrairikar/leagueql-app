# BE-015: Stripe Billing — Checkout, Webhook & Subscription Lifecycle

> **Feature-flagged ([BE-017](BE-017-feature-flags.md)).** Billing is active only when the
> `billing` flag is ON. When OFF (the current default), `POST /leagues/{id}/checkout-session`
> and `POST /billing-portal-session` return `404`, and the Stripe webhook returns a `200`
> no-op without writing subscription state.

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
  Session in `subscription` mode with `subscription_data.metadata` carrying
  `canonical_league_id` **plus the native `platform` and `native_league_id`** (so the webhook
  can write the durable trial record without a reverse lookup — see the trial edge case) and
  `subscription_data.trial_period_days` (included only when the league has no recorded
  `trial_used` — checked against **both** the `METADATA` marker and the durable
  `(platform, native_league_id)` record; see the trial edge case), sets
  `allow_promotion_codes=True` so the Stripe-hosted
  page renders an "Add promotion code" field, and returns the session URL. Customers redeem a
  **promotion code** (a customer-facing code mapped to a Stripe coupon — e.g. the founders
  100%-off coupon), not a bare coupon, which has no redeemable code. The session also sets
  `managed_payments={"enabled": True}` so Stripe acts as **merchant of record** (Managed
  Payments) — handling indirect-tax compliance, fraud, disputes, and buyer support. Managed
  Payments must be activated at the account level and the product must carry an eligible tax
  code (the LeagueQL subscription uses `txcd_10000000`, Electronically Supplied Services); it
  applies only to new subscriptions opened through a Managed Payments session. Returns `409`
  when the league already has an active subscription or an unexpired in-flight checkout.
- **Webhook endpoint / Lambda** (no Clerk auth; `Stripe-Signature` verified): `POST
  /stripe/webhook` — on `checkout.session.completed`,
  `customer.subscription.created|updated`, and `invoice.paid`, calls
  `common.subscription.record_active_subscription(...)`; on `customer.subscription.deleted`
  or terminal payment failure, calls `common.subscription.expire_subscription(...)` which sets
  `subscription_end_time` to the past (gate flips to expired live). When the recorded
  subscription is *trialing*, it also writes the durable `TRIAL_USED` record keyed by the
  `(platform, native_league_id)` read from the subscription metadata (see the trial edge case).
- **Billing portal endpoint** (Clerk-authed): `POST /billing-portal-session` — returns a
  Stripe Billing Portal URL for the user's Customer (update card / cancel). Cancellation is
  configured to take effect **immediately** (not at period end). Backs the frontend "Manage
  Subscription" dialog ([FE-021](../frontend/FE-021-subscription-access-control.md)).
- **Mapping (schema):** `stripe_customer_id` stored once per user (a `USER#{clerk_user_id}`
  item); on the league `METADATA` item — `stripe_subscription_id`, `pending_checkout`
  (in-flight checkout marker `{token, expires_at, user_id}` with a short TTL, cleared by the
  webhook on success), and `trial_used` (set when the league's first trial is granted, never
  cleared); a durable **`TRIAL_USED` item** keyed by
  `PK = LEAGUE#{native_league_id}#PLATFORM#{platform}`, `SK = TRIAL_USED` (no
  `canonical_league_id` attribute, so it outlives league deletion — see the trial edge case);
  and `canonical_league_id`, `platform`, and `native_league_id` in the Stripe subscription
  metadata. Documented in `docs/db/dynamodb_spec.md`.
- **Secrets & environment mode:** the Stripe secret key and webhook signing secret are stored
  as **SecureString SSM Parameter Store** parameters (`/leagueql/{env}/stripe/secret_key` and
  `/leagueql/{env}/stripe/webhook_secret`) and fetched at Lambda **cold start** by parameter
  *name* — the name is passed via the non-sensitive `STRIPE_SECRET_KEY_SSM_PARAM` /
  `STRIPE_WEBHOOK_SECRET_SSM_PARAM` env vars (`src/common/secrets.py`). The secret **value**
  never appears in Lambda environment variables, Terraform state, or CI. The values are set
  out-of-band via the AWS CLI (per region); Terraform only grants the API and webhook Lambda
  roles `ssm:GetParameter` on the specific parameter ARNs and never reads or writes the values.
  The non-sensitive `stripe_price_id` remains an ordinary Terraform var / env var. Never
  committed or logged.
  **DEV uses Stripe sandbox (test) mode and PROD uses live mode** — each environment is
  configured with its own mode-specific credentials (`sk_test_…`/`sk_live_…`, the matching
  `whsec_…` webhook signing secret) and its own mode-specific Price/Product IDs. Test- and
  live-mode objects (Customers, Subscriptions, Prices, webhook endpoints) are fully isolated
  by Stripe, so no resource is shared across environments.
- **Reuses** BE-014's `require_active_subscription` (enforcement) **unchanged**. The sole
  write path is `common.subscription` (`record_active_subscription` / `expire_subscription`) —
  shared, conditional, multi-attribute writes vendored into both the API and webhook Lambda
  zips (the webhook is a separate Lambda and cannot import `src/api/helpers.py`). See
  Idempotency Layer 3.

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
      OR pending_checkout.expires_at < :now OR pending_checkout.user_id = :uid)`. DynamoDB
      serializes concurrent attempts so only one wins; a *different* user gets `409` and creates
      no session, while the **initiating user can re-claim immediately** (so abandoning one's own
      checkout doesn't block retrying it). The `expires_at` TTL lets a marker held by another
      user self-heal, and reconciliation backstops any true duplicate subscription.
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
- **Layer 3 — state convergence (handles out-of-order):** the write is
  `common.subscription.record_active_subscription` — a single conditional, multi-attribute
  `UpdateItem` that applies the monotonic guard, claims `stripe_subscription_id`, and clears
  `pending_checkout`.
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
  `trial_used` marker, set when the first trial is granted and never cleared; checkout omits
  the trial whenever it is present. (Trials remain independent *across different* leagues —
  each league gets its single trial.)
- **Trial usage survives league deletion (durable record):** the `METADATA` `trial_used`
  marker is destroyed when a league is deleted ([BE-007](BE-007-delete-league-api.md)), and a
  re-onboarded league is minted with a **new** `canonical_league_id` — so a marker keyed by
  canonical ID could not block trial reuse after delete + re-onboard. To prevent trial
  farming, trial usage is **also** recorded in a durable item keyed by the platform-native
  identity that *does* survive — `(platform, native_league_id)` — written when the trial is
  granted and **never** removed by league deletion:
  - **Key (no `canonical_league_id` attribute):** `PK = LEAGUE#{native_league_id}#PLATFORM#{platform}`,
    `SK = TRIAL_USED` — the same PK as the league's `LEAGUE_LOOKUP` item. It deliberately
    carries **no** `canonical_league_id` attribute so the BE-007 delete sweep (which finds
    items by `PK = LEAGUE#{canonical_league_id}` and by a GSI1 query on `canonical_league_id`)
    never matches it.
  - **Writer (webhook):** when recording a *trialing* subscription, the webhook writes this
    item in addition to the `METADATA` `trial_used`. To avoid a reverse GSI lookup, the native
    `platform` and `native_league_id` are carried in the Stripe **subscription metadata**
    (added at checkout, alongside `canonical_league_id`) so the webhook has them directly from
    the event payload.
  - **Reader (checkout):** checkout already has `(platform, leagueId)` as request params, so it
    reads this item directly and treats the trial as used when **either** the `METADATA`
    `trial_used` **or** the durable `(platform, native_league_id)` record is present.
  - **Scope note:** this is **per league regardless of account** — deleting and re-onboarding
    the same league under a *different* user still finds the durable record, so the trial does
    not reset. The retained record contains only a platform + league ID (no personal data).
- **One user, many leagues:** a single Customer holds multiple Subscriptions; each webhook
  event routes by `metadata.canonical_league_id` and each league is gated independently.
- **Customer first use / concurrency:** the Clerk user ↔ Stripe Customer mapping is created
  on demand; concurrent first-checkout requests must not create duplicate Customers (look up
  by `clerk_user_id` and/or use a Stripe idempotency key).
- **Stored Stripe Customer deleted out-of-band:** the `USER#{clerk_user_id}` mapping can point
  at a Customer that was deleted from the Stripe dashboard; opening a Checkout Session against
  it raises a `No such customer` `InvalidRequestError`. Checkout **recovers**: it mints a fresh
  Customer (with a *unique* idempotency key so the create is not deduplicated back to the
  deleted Customer), overwrites the stored mapping, and retries the session **once** (with a new
  idempotency key), so the user can subscribe without manual intervention. Any **other** Stripe
  error creating the session surfaces as a `502` with a JSON `detail` so
  [FE-022](../frontend/FE-022-subscription-checkout.md) shows it inline next to the Subscribe
  button — rather than an **uncaught `500`**, which (being raised above the CORS middleware)
  ships without CORS headers and leaves the browser unable to read the response, so the UI shows
  nothing.
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
- [ ] A Checkout Session opened against a **deleted** Stripe Customer recovers by minting a new
      Customer, overwriting the stored `USER#{clerk_user_id}` mapping, and retrying once; any
      other Stripe error returns a `502` with a JSON `detail` rather than an uncaught `500`.
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
- [ ] Trial usage is recorded in a durable `(platform, native_league_id)` item that is **not**
      removed when the league is deleted, and a league deleted then re-onboarded (even under a
      different account) is created with **no trial**.
- [ ] The durable `TRIAL_USED` item carries no `canonical_league_id` attribute and is not
      removed by the BE-007 delete sweep.
- [ ] Webhook processing is idempotent — duplicate or out-of-order deliveries never regress
      `subscription_end_time`.
- [ ] A single user can hold active subscriptions for multiple leagues simultaneously, each
      gated independently by BE-014.
- [ ] A second checkout attempt for a league with an active subscription, **or** with an
      unexpired `pending_checkout` marker held by a **different** user, returns `409` and creates
      no Stripe Checkout Session.
- [ ] The user who started a checkout can re-attempt immediately (re-claiming their own
      `pending_checkout` marker) without a `409`.
- [ ] The `pending_checkout` marker is claimed via a conditional write (only one of two
      concurrent attempts by *different* users wins) and is cleared by the webhook once the
      subscription is recorded; an expired marker no longer blocks a new checkout.
- [ ] If a duplicate subscription is ever created for a league, the webhook reconciles to a
      single active subscription by canceling the extra, leaving exactly one
      `stripe_subscription_id` on `METADATA`.
- [ ] `POST /billing-portal-session` returns a Stripe Billing Portal URL for the user's
      Customer.
- [x] The client-supplied `subscriptionEndTime` onboarding input is removed;
      `subscription_end_time` is set only server-side via this flow (supersedes the
      [BE-001](BE-001-league-onboarding.md) interim behavior).
- [ ] Stripe secret key and webhook signing secret are stored as SecureString SSM parameters
      and fetched by the Lambdas at runtime; they are never injected as Lambda env vars,
      written to Terraform state, present in CI, or committed/logged.
- [ ] DEV is configured with Stripe sandbox (test) mode credentials and Price IDs; PROD is
      configured with live mode; neither environment carries the other's keys.

## Implementation Notes
- **Stripe SDK access gotcha (v15):** stripe-python resource objects (e.g. `Subscription`,
  `Event`) are **not** `dict` subclasses and have **no `.get()`** — `obj.get(...)` raises
  `AttributeError: get`. The webhook handler reads Stripe-object fields via a subscript-based
  `_get(obj, key, default)` helper (`obj[key]` with `KeyError`/`TypeError` fallback), which works
  on both real Stripe objects and the plain-dict test fixtures. The checkout/portal paths already
  use subscript (`session["url"]`, `customer["id"]`), so they were unaffected.
- **The subscription write moved out of `src/api/helpers.py` into `common/subscription.py`.**
  The webhook is a separate Lambda and cannot import the API package, so the BE-014
  `update_subscription_end_time` helper (an unconditional single-attribute `SET`) was removed
  and replaced by `common.subscription.record_active_subscription` / `expire_subscription`
  (conditional, multi-attribute writes), vendored into both Lambda zips. The old
  `TestUpdateSubscriptionEndTime` was removed; coverage now lives in
  `tests/unit/common/test_subscription.py`.
- **Infrastructure (now implemented).** The `stripe_webhook` Lambda is deployed per-region
  (like the API Lambda) with its own IAM role (logs + DynamoDB `GetItem`/`PutItem`/`UpdateItem`
  on the primary + replica tables). The `POST /stripe/webhook` route is declared in the
  templated OpenAPI spec via a `${stripe_webhook_lambda_arn}` var and is **unauthenticated**
  (no Clerk security scheme — Stripe signature verification is the auth); API Gateway is granted
  invoke permission on the webhook Lambda in `regional/main.tf`. Stripe config reaches both
  Lambdas as environment variables; the return URLs are derived from `environment` (prod →
  `https://leagueql.com`, dev → `http://localhost:5173`). Checkout **success**, **cancel**, and
  the Billing Portal **return** all target the in-app dashboard home (`…/home`, under the
  SubscriptionGuard). Success carries `?checkout=success`, which drives the activation poll in
  `useSubscription` ([FE-022](../frontend/FE-022-subscription-checkout.md)); cancel has no param,
  so it never polls. CI builds/zips the new Lambda and passes the non-sensitive `stripe_price_id`
  as `TF_VAR_*` (mode-selected by environment); the secret key and webhook signing secret are
  **no longer in CI** — they live in SSM Parameter Store (see *Secrets & environment mode* and
  the one-time setup below) and are fetched at runtime via `src/common/secrets.py`.
- **`pending_checkout` self-heal window is configurable** via the `CHECKOUT_PENDING_TTL_MINUTES`
  env var (`main.py`, default 30); Terraform sets **5 in dev / 30 in prod** so abandoned-checkout
  retries unblock quickly in dev. Until it lapses (or the webhook records the subscription), a
  repeat checkout returns `409`.
- **One-time operational setup** (cannot be Terraformed — the webhook signing secret only exists
  after the endpoint is registered in Stripe, and the secret values are set out-of-band so they
  never enter Terraform state): set both SecureString SSM parameters **per region**
  (`us-east-1` + `us-west-2`) via the AWS CLI — `aws ssm put-parameter --type SecureString` for
  `/leagueql/{env}/stripe/secret_key` and `/leagueql/{env}/stripe/webhook_secret`. See the
  runbook [`docs/deploy/stripe-webhook-setup.md`](../../deploy/stripe-webhook-setup.md).

## Authorization (BE-016)
Checkout (`POST /leagues/{id}/checkout-session`) is **owner-gated** ([BE-016](BE-016-league-ownership-authorization.md)); the per-user billing portal is unchanged.

## Sources
`src/api/routes.py` (`create_checkout_session`, `create_billing_portal_session`,
`get_authenticated_user`), `src/api/helpers.py` (`get_or_create_stripe_customer`,
`get_stripe_customer_id`, `claim_pending_checkout`; `require_active_subscription` — reused
unchanged), `src/api/main.py` (Stripe config + `main.stripe`), `src/common/secrets.py` (SSM parameter
fetch), `src/common/subscription.py`
(`record_active_subscription`, `expire_subscription`), `src/stripe_webhook/handler.py`,
`docs/api/openapi_spec.yaml` (checkout, billing-portal, `POST /stripe/webhook`),
`docs/db/dynamodb_spec.md` (`stripe_subscription_id`, `pending_checkout`, `trial_used` on
METADATA; `USER` item; `WEBHOOK_EVENT` dedup item),
`infrastructure/regional/main.tf` + `vars.tf` (webhook Lambda, invoke permission, `stripe_price_id`
+ SSM param-name env vars, alarm), `infrastructure/global/{dev,prod}/main.tf` (API + webhook IAM
roles, incl. `ssm:GetParameter` on the Stripe parameter ARNs),
`.github/workflows/build.yaml` (build + `TF_VAR_*` wiring),
[BE-014](BE-014-subscription-access-control.md), [BE-001](BE-001-league-onboarding.md).
