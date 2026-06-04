Feature: Subscription checkout and billing portal (FE-022, FE-023)
  The paywall starts Stripe Checkout; an active subscription opens the Stripe
  Billing Portal. Backend errors surface inline next to the button.

  Scenario: Subscribe redirects to Stripe Checkout
    Given a checkout session will be created
    When I click Subscribe on the paywall
    Then the browser is redirected to the Stripe URL

  Scenario: A 409 on checkout shows an inline error
    Given checkout is rejected because a subscription already exists
    When I click Subscribe on the paywall
    Then I see an inline error "A subscription is already active for this league"

  Scenario: A server error on checkout shows an inline error
    Given checkout fails with a server error
    When I click Subscribe on the paywall
    Then I see an inline error "Couldn't start checkout. Please try again."

  Scenario: Manage billing redirects to the Stripe portal
    Given the league has an active subscription and a billing portal session
    When I click Manage billing in the dialog
    Then the browser is redirected to the Stripe URL
