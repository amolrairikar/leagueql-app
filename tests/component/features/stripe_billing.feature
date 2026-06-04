Feature: Stripe billing checkout and webhook lifecycle (BE-015)
  Checkout resolves the caller's Stripe customer and opens a session; the webhook
  is the single writer of subscription_end_time. The webhook verifies the
  signature, dedups on the Stripe event id, and converges subscription state via
  conditional DynamoDB writes — all idempotent under at-least-once delivery.

  Scenario: Checkout recovers when the stored Stripe customer was deleted
    Given a checkout-ready league "canon-1" native "100" on "SLEEPER" for user "user_1"
    And user "user_1" has a stored Stripe customer "cus_old" that was deleted in Stripe
    When user "user_1" starts checkout for league "100" on "SLEEPER"
    Then the checkout endpoint responds 200 with a session URL
    And user "user_1" now maps to a freshly created Stripe customer

  Scenario: A completed trial checkout records the subscription and durable trial marker
    Given a subscribable league "canon-1" native "100" on "SLEEPER"
    When Stripe sends a "checkout.session.completed" webhook (event "evt_1") for subscription "sub_1" with status "trialing"
    Then the webhook responds with status 200
    And league "canon-1" has a subscription_end_time
    And a durable TRIAL_USED marker exists for native league "100" on "SLEEPER"
    And a WEBHOOK_EVENT dedup marker exists for event "evt_1"

  Scenario: A redelivered event is ignored (dedup)
    Given a subscribable league "canon-1" native "100" on "SLEEPER"
    When Stripe sends a "checkout.session.completed" webhook (event "evt_1") for subscription "sub_1" with status "trialing"
    And Stripe sends a "checkout.session.completed" webhook (event "evt_1") for subscription "sub_1" with status "trialing"
    Then the webhook responds with status 200

  Scenario: An invalid signature is rejected without state change
    Given a subscribable league "canon-1" native "100" on "SLEEPER"
    When Stripe sends a webhook with an invalid signature
    Then the webhook responds with status 400
    And no WEBHOOK_EVENT dedup marker exists for event "evt_1"

  Scenario: Cancellation expires access scoped to the recorded subscription
    Given a subscribable league "canon-1" native "100" on "SLEEPER"
    And league "canon-1" already records subscription "sub_1"
    When Stripe sends a "customer.subscription.deleted" webhook (event "evt_del") for subscription "sub_1" with status "canceled"
    Then the webhook responds with status 200
    And league "canon-1" subscription is expired

  Scenario: A second subscription for the league is reconciled by cancellation
    Given a subscribable league "canon-1" native "100" on "SLEEPER"
    And league "canon-1" already records subscription "sub_1"
    When Stripe sends a "customer.subscription.updated" webhook (event "evt_2") for subscription "sub_2" with status "active"
    Then the webhook responds with status 200
    And the duplicate subscription was canceled
