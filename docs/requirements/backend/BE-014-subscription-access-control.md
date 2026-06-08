# BE-014: Subscription Access Control

> **Feature-flagged ([BE-017](BE-017-feature-flags.md)).** This gate is active only when the
> `billing` flag is ON. When OFF (the current default), `require_active_subscription` is a
> no-op and every league reaches the gated endpoints with full access.

## Description
Enforces a per-league subscription on the backend API. Each league's `METADATA` item carries a
`subscription_end_time` (ISO 8601 UTC timestamp). A league's subscription is **active** while
`now < subscription_end_time`; it is **expired** when the timestamp is in the past **or absent**.
Expired leagues are blocked from the data and write endpoints (HTTP `402`), while the metadata
and delete endpoints stay reachable so the frontend can read status and users can remove a
league. State is evaluated live on each request — there is no stored status flag and no
scheduled job. The actual `subscription_end_time` value is written **server-side by the Stripe
billing webhook** ([BE-015](BE-015-stripe-billing.md)); this gate only *reads* it. Onboarding
([BE-001](BE-001-league-onboarding.md)) does **not** write it — the former client-supplied
`subscriptionEndTime` input was a spoofable stopgap and has been removed.

## Scope
- Helper: `require_active_subscription(canonical_league_id)` (`src/api/helpers.py`) — reads the
  `METADATA` item via `get_league_metadata` and raises `402 Subscription required` when
  `subscription_end_time` is absent or `<= now` (UTC).
- Write path: `common.subscription` (`record_active_subscription` / `expire_subscription`,
  `src/common/subscription.py`) — the sole writer of `subscription_end_time`, called by the
  Stripe billing webhook ([BE-015](BE-015-stripe-billing.md)). (This replaced the earlier
  `update_subscription_end_time` helper, which is removed.)
- **Gated** endpoints (`src/api/routes.py`): `GET /leagues/{id}/query`,
  `POST /leagues/{id}/migrate`, `POST /leagues/{id}/espn_members`, and `POST /leagues`
  **only on the REFRESH path for an already-onboarded league**.
- **Ungated** endpoints: `GET /leagues/{id}` (must stay readable), `DELETE /leagues/{id}`,
  `GET /jobs/{id}`, and new-league `ONBOARD` (no league exists yet to check).

## Edge Cases
- **`subscription_end_time` absent:** treated as expired → `402`.
- **Timestamp exactly equal to now:** treated as expired (`<= now` blocks).
- **New onboarding:** allowed regardless (the league/subscription does not exist yet). The
  onboarder does **not** write `subscription_end_time` ([BE-001](BE-001-league-onboarding.md));
  the value is set only by the Stripe webhook ([BE-015](BE-015-stripe-billing.md)), so a
  freshly onboarded, unsubscribed league reads as expired until checkout completes.
- **Reading status while expired:** `GET /leagues/{id}` is never gated, so the frontend can
  always read `subscription_end_time` to render its paywall ([FE-021](../frontend/FE-021-subscription-access-control.md)).
- **Delete while expired:** allowed, so users can clean up lapsed leagues.
- **Existing leagues (no value):** without a backfill they read as expired; a one-off backfill
  of `subscription_end_time` is required before/with deploy.

## Acceptance Criteria
- [ ] A league with `subscription_end_time` in the future reaches gated endpoints (`200`/`202`).
- [ ] A league with a past or absent `subscription_end_time` receives `402` from gated endpoints.
- [ ] `GET /leagues/{id}` and `DELETE /leagues/{id}` succeed regardless of subscription state.
- [ ] New-league `ONBOARD` is never blocked by the gate.
- [ ] REFRESH of an already-onboarded, expired league returns `402`.
- [ ] **Enforcement** introduces no scheduled job, EventBridge rule, or polling — state is
      evaluated live per request, and this gate adds no infrastructure of its own. (The
      `subscription_end_time` value is written by the event-driven Stripe webhook in
      [BE-015](BE-015-stripe-billing.md), which is that feature's Lambda, not this one's.)

## Sources
`src/api/helpers.py` (`require_active_subscription`),
`src/common/subscription.py` (`record_active_subscription`, `expire_subscription`),
`src/api/routes.py`, `docs/db/dynamodb_spec.md` (METADATA `subscription_end_time`),
`docs/api/openapi_spec.yaml`.
