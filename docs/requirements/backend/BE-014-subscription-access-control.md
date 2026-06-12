# BE-014: Subscription Access Control

> **Per-feature paywall, feature-flagged ([BE-017](BE-017-feature-flags.md)).** LeagueQL is
> **freemium**: the app is free except for **premium features**. The generic gate
> `require_active_subscription(canonical_league_id, paywall_flag)` exists and is unit-tested, but
> **no production endpoint currently calls it** — there is no real premium feature yet. It is
> retained infrastructure: a placeholder flag `paywall_test_feature` and the pricing table keep
> the mechanism wired and ready. A future premium endpoint would call the gate; it only enforces
> when **both** `billing` and that feature's per-feature flag are ON.

## Description
Provides the per-league subscription gate used by **premium** backend endpoints (none today).
Each league's `METADATA` item carries a `subscription_end_time` (ISO 8601 UTC timestamp). A
league's subscription is **active** while `now < subscription_end_time`; it is **expired** when the
timestamp is in the past **or absent**. When a premium feature is paywalled (both flags ON), the
gate blocks an expired league from that feature's endpoint (HTTP `402`); everything else stays
reachable. State is evaluated live on each request — there is no stored status flag and no
scheduled job. The actual `subscription_end_time` value is written **server-side by the Stripe
billing webhook** ([BE-015](BE-015-stripe-billing.md)); this gate only *reads* it. Onboarding
([BE-001](BE-001-league-onboarding.md)) does **not** write it — the former client-supplied
`subscriptionEndTime` input was a spoofable stopgap and has been removed.

> **Note on League Migration.** Migration was briefly modeled as the first premium feature, but a
> one-time platform move cannot be "un-granted" if a subscription later lapses, so it is **not**
> gated. It is free ([BE-003](BE-003-league-migration.md)).

## Scope
- Helper: `require_active_subscription(canonical_league_id, paywall_flag)` (`src/api/helpers.py`)
  — returns early (no-op) when `is_feature_paywalled(paywall_flag)` is false (billing off or the
  feature's flag off; see [BE-017](BE-017-feature-flags.md)); otherwise reads the `METADATA` item
  via `get_league_metadata` and raises `402 Subscription required` when `subscription_end_time` is
  absent or `<= now` (UTC). **No route calls this yet** — it is exercised only by unit tests.
- Write path: `common.subscription` (`record_active_subscription` / `expire_subscription`,
  `src/common/subscription.py`) — the sole writer of `subscription_end_time`, called by the
  Stripe billing webhook ([BE-015](BE-015-stripe-billing.md)). (This replaced the earlier
  `update_subscription_end_time` helper, which is removed.)
- **Gated endpoints:** none currently. To gate a future premium endpoint, call the helper with
  that feature's `paywall_*` flag.
- **Ungated endpoints:** all of them — including `POST /leagues/{id}/migrate`, `GET /leagues/{id}/query`,
  `POST /leagues/{id}/espn_members`, `POST /leagues` (REFRESH and ONBOARD), `GET /leagues/{id}`,
  `DELETE /leagues/{id}`, and `GET /jobs/{id}`.

## Edge Cases
- **No endpoint gated:** with no production call site, no endpoint returns `402` for subscription
  reasons today, regardless of flag state.
- **Helper, both flags ON, `subscription_end_time` absent / `<= now`:** treated as expired →
  raises `402` (unit-level behavior).
- **Helper, billing OFF or the feature flag OFF:** no-op; never reads `subscription_end_time`.
- **Timestamp exactly equal to now:** treated as expired (`<= now` blocks).
- **Reading status:** `GET /leagues/{id}` is never gated, so the frontend can always read
  `subscription_end_time` ([FE-021](../frontend/FE-021-subscription-access-control.md)).

## Acceptance Criteria
- [ ] `require_active_subscription` raises `402` when the feature is paywalled (both flags ON) and
      `subscription_end_time` is absent or `<= now`.
- [ ] `require_active_subscription` is a no-op when billing is OFF **or** the named per-feature
      flag is OFF, and does not read `METADATA`.
- [ ] No production endpoint returns a subscription `402` today (the helper has no route call site).
- [ ] `GET /leagues/{id}` and `DELETE /leagues/{id}` succeed regardless of subscription state.
- [ ] The gate introduces no scheduled job, EventBridge rule, or polling — state is evaluated live
      per call. (The `subscription_end_time` value is written by the event-driven Stripe webhook in
      [BE-015](BE-015-stripe-billing.md), not here.)

## Sources
`src/api/helpers.py` (`require_active_subscription`),
`src/common/subscription.py` (`record_active_subscription`, `expire_subscription`),
`src/common/feature_flags.py` (`is_feature_paywalled`, `PAYWALL_TEST_FEATURE`),
`docs/db/dynamodb_spec.md` (METADATA `subscription_end_time`), `docs/api/openapi_spec.yaml`.
