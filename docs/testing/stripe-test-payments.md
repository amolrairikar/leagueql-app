# Testing: Stripe Payments in DEV

DEV runs Stripe in **sandbox (test) mode** (the `sk_test_…` keys — see
[BE-015](../requirements/backend/BE-015-stripe-billing.md)). Test mode is fully isolated from
live mode and **never moves real money**, but it only accepts Stripe's designated **test card
numbers** — random digits fail card validation (Luhn check) and are rejected.

## Use this card for a successful checkout

| Field | Value |
|---|---|
| Number | `4242 4242 4242 4242` (Visa, always succeeds) |
| Expiry | any **future** date, e.g. `12/34` |
| CVC | any 3 digits, e.g. `123` |
| ZIP / postal | any, e.g. `42424` |
| Name / email | anything |

## What happens in our flow

Checkout includes a trial (`STRIPE_TRIAL_PERIOD_DAYS`, default 14), so Stripe **collects** the
card but **does not charge** it immediately. After you submit the `4242` card:

1. The subscription is created with `status: trialing`.
2. Stripe fires `checkout.session.completed` + `customer.subscription.created`.
3. The webhook records `subscription_end_time = trial_end` and clears `pending_checkout`.

The league's paywall then lifts (the analytics pages render).

## Other test cards (specific scenarios)

| Card | Behavior |
|---|---|
| `4000 0000 0000 0002` | Declined |
| `4000 0025 0000 3155` | Requires 3-D Secure authentication (tests the auth modal) |
| `4000 0000 0000 9995` | Declined — insufficient funds |

Full list: https://stripe.com/docs/testing

## Abandoned checkouts

If you abandon a checkout (Stripe's "← back" link, browser back, or closing the tab), the
`pending_checkout` marker records **your** `clerk_user_id`, so **you can retry immediately** — the
same user re-claims their own marker (no `409`). A `409 "A subscription or checkout is already
active for this league"` only happens when:
- the league already has an active subscription, or
- a **different** user holds an unexpired in-flight checkout (that marker self-heals after
  **5 minutes in dev** / 30 in prod, and reconciliation cancels any true duplicate).

So during manual testing you can re-attempt checkout for the same league as the same signed-in
user as often as you like. (Completing the `4242` flow still clears the marker immediately via the
webhook.)

## Related
- Backend billing feature: [BE-015](../requirements/backend/BE-015-stripe-billing.md)
- Webhook endpoint setup: [`docs/deploy/stripe-webhook-setup.md`](../deploy/stripe-webhook-setup.md)
