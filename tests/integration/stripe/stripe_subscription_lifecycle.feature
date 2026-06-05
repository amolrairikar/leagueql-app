Feature: Stripe subscription lifecycle integration
  Drives the BE-015 webhook — the single writer of subscription_end_time — end to
  end against Stripe sandbox (test) mode. Stripe's hosted Checkout page cannot be
  completed via the API, so instead of submitting the 4242 4242 4242 4242 card on
  that page, the test creates a real test-mode subscription via the Stripe API
  using the equivalent test payment method (pm_card_visa). Stripe then delivers
  real webhook events to the deployed dev /stripe/webhook endpoint, and the
  assertions read the subscription_end_time the webhook converges onto the
  league's METADATA item (polled, since delivery is asynchronous).

  Runs after the onboarding integration tests, so the Sleeper test league already
  exists in DynamoDB. Each scenario tears down the test-mode subscription/customer
  and the subscription attributes it wrote (see environment.after_scenario).

  Background:
    Given a Sleeper league exists in DynamoDB
    And the league has no recorded subscription

  Scenario: A trialing subscription's webhook records subscription_end_time
    When a trialing subscription is created for the league with the test card
    Then subscription_end_time on the league converges to the subscription trial_end

  Scenario: Canceling the subscription expires access immediately
    Given a trialing subscription has been recorded for the league
    When the subscription is canceled
    Then subscription_end_time on the league is set to the past

  Scenario: A declined card does not grant the league access
    When a no-trial subscription is created for the league with a declined card
    Then the league is not granted access
