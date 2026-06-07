# BE-007: Delete League API

## Description
Deletes an onboarded league and all of its associated data. `DELETE /leagues/{leagueId}`
resolves the canonical league ID, **cancels the league's active Stripe subscription (if
any)**, then removes all DynamoDB items for the league, deletes the raw API payloads from S3,
and decrements the global `LEAGUE_COUNT`.

Because each league has its own Stripe subscription ([BE-015](BE-015-stripe-billing.md)) and
the subscription pointer (`stripe_subscription_id`) lives on the league's `METADATA` item —
which this endpoint deletes — the subscription **must** be canceled as part of deletion.
Otherwise Stripe keeps billing the customer for a league that no longer exists, and the app
loses the only pointer it had to cancel or reconcile that subscription.

**Ordering — cancel first, then delete.** The endpoint reads `stripe_subscription_id` from
`METADATA` and cancels the subscription in Stripe **before** removing any items, so the data
is never destroyed while a live subscription still points at it. A failed cancellation aborts
the delete (returns `500`) with all data intact for retry; the data is removed only once the
subscription is confirmed canceled (or absent / already canceled).

## Scope
- Endpoint: `DELETE /leagues/{leagueId}?platform=` (`src/api/routes.py::delete_league`).
- Helpers: `delete_all_league_items`, `update_league_count`.
- S3 prefix deleted: `raw-api-data/{canonical_league_id}/`.
- **Subscription cancellation (runs first):** read `stripe_subscription_id` from `METADATA`
  and, if present, cancel the subscription in Stripe **immediately** (consistent with BE-015's
  immediate-cancellation policy — not at period end) **before** deleting any items. Use a
  Stripe idempotency key so a retried delete does not error on an already-canceled
  subscription. The resulting `customer.subscription.deleted` webhook is a no-op here (the
  league's items, including `METADATA`, are gone by the time it lands — see the webhook edge
  case).

## Edge Cases
- **League not onboarded:** lookup miss returns `404`.
- **No active subscription:** league has no `stripe_subscription_id` (never subscribed, or
  subscription already canceled) → skip the Stripe call and proceed with deletion.
- **Subscription already canceled in Stripe:** cancellation is idempotent — an
  already-canceled / not-found subscription is treated as success, not a `500`.
- **Stripe cancellation fails (network/5xx):** deletion **stops** and returns `500` before
  any items are removed, so the `stripe_subscription_id` pointer is preserved for a retry
  (deleting the data first would orphan a live, unrecoverable subscription).
- **Late `customer.subscription.deleted` webhook after deletion:** the league's `METADATA`
  item no longer exists, so BE-015's `expire_subscription` write is a no-op — its
  `attribute_exists(PK)` condition fails rather than resurrecting a zombie `METADATA` item
  (already implemented in `common.subscription`).
- **Re-onboarding a deleted league does NOT regrant the trial:** the delete sweep removes the
  league's `METADATA` (including its `trial_used` marker), but trial usage is also recorded in
  a durable `(platform, native_league_id)` item that carries no `canonical_league_id` and so
  is **not** matched by the sweep ([BE-015](BE-015-stripe-billing.md) trial edge case). A
  league deleted then re-onboarded — even under a different account — is therefore created
  with **no trial**.
- **No S3 objects present:** delete proceeds (S3 deletion is best-effort / no-op if empty).
- **>1000 S3 objects:** S3 `delete_objects` handles up to 1,000 keys per request;
  larger sets must be batched.
- **DynamoDB/S3 client error:** return `500` "Failed to delete league".
- **`LEAGUE_LOOKUP` entries across platforms (migrated league):** all lookup entries for
  the canonical league must be removed, not just the one queried.
- **Idempotency:** deleting an already-deleted league should not leave `LEAGUE_COUNT`
  inconsistent.

## Acceptance Criteria
- [ ] `DELETE /leagues/{leagueId}` for an onboarded league returns `200` "Successfully
      deleted league".
- [ ] Deleting a league with an active subscription cancels that Stripe subscription
      immediately; the customer is not billed again for the deleted league.
- [ ] Cancellation happens **before** any DynamoDB/S3 deletion; if it fails, the endpoint
      returns `500` and leaves all league data (including `stripe_subscription_id`) intact
      for retry.
- [ ] Deleting a league with no `stripe_subscription_id` skips the Stripe call and still
      succeeds.
- [ ] Subscription cancellation is idempotent — deleting a league whose subscription is
      already canceled does not return `500`.
- [ ] All DynamoDB items (metadata, lookups, precomputed views) for the canonical league
      are removed.
- [ ] The durable `TRIAL_USED` marker (keyed by `(platform, native_league_id)`, carrying
      no `canonical_league_id`) is **not** removed by the delete sweep, so re-onboarding the
      same league does not regrant a free trial (see [BE-015](BE-015-stripe-billing.md)).
- [ ] All raw API payloads under the league's S3 prefix are deleted.
- [ ] `LEAGUE_COUNT` is decremented by 1.
- [ ] Deleting an un-onboarded league returns `404`.
- [ ] Backend errors during deletion return `500`.

## Authorization (BE-016)
Delete is **owner-gated** ([BE-016](BE-016-league-ownership-authorization.md)): only the league owner can delete; a non-owner gets `403` before any data is touched.

## Sources
`src/api/routes.py::delete_league`, `src/api/helpers.py` (`delete_all_league_items`;
subscription-cancellation helper, e.g. `cancel_league_subscription`),
`docs/api/openapi_spec.yaml`, [BE-015](BE-015-stripe-billing.md).
