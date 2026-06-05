Feature: Stripe billing integration
  Exercises the deployed billing endpoints against Stripe sandbox (test) mode
  (BE-015): checkout-session creation, the in-flight pending_checkout marker,
  the billing portal, and Clerk-auth enforcement. The browser-driven card flow
  (docs/testing/stripe-test-payments.md) cannot be automated headlessly, so
  these scenarios stop at the returned Stripe-hosted URL — no card is submitted
  and no money moves.

  The suite runs after the onboarding integration tests, so the Sleeper test
  league already exists in DynamoDB.

  Background:
    Given a Sleeper league exists in DynamoDB
    And the test league has no in-flight checkout

  Scenario: Authenticated checkout returns a Stripe URL and records a pending_checkout marker
    When the user requests a checkout session for the test league
    Then the API responds 200 with a Stripe checkout URL
    And a pending_checkout marker is recorded on the league for the user

  Scenario: The initiating user can re-attempt checkout without a 409
    Given the user has an in-flight checkout for the test league
    When the user requests a checkout session for the test league
    Then the API responds 200 with a Stripe checkout URL

  Scenario: Checkout requires authentication
    When an unauthenticated checkout request is made for the test league
    Then the API rejects the request as unauthorized

  Scenario: Billing portal returns a management URL for the user
    Given the user has a Stripe customer
    When the user requests a billing portal session
    Then the API responds 200 with a Stripe billing portal URL

  Scenario: Billing portal requires authentication
    When an unauthenticated billing portal request is made
    Then the API rejects the request as unauthorized
