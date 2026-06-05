Feature: Stripe webhook integration
  The POST /stripe/webhook endpoint is unauthenticated — Stripe signature
  verification is the auth (BE-015). It must reject any payload whose
  Stripe-Signature cannot be verified with the configured signing secret (a
  forged signature, or a test-vs-live mode mismatch), returning 400 with no
  state change. These scenarios post a payload that is never validly signed, so
  no subscription state is written.

  Scenario: A webhook with an invalid Stripe-Signature is rejected
    When a webhook event is posted with an invalid Stripe-Signature
    Then the webhook is rejected with 400

  Scenario: A webhook with no Stripe-Signature is rejected
    When a webhook event is posted with no Stripe-Signature
    Then the webhook is rejected with 400
