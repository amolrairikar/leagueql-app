Feature: Subscription checkout and billing portal (FE-022, FE-023)
  The paywall starts Stripe Checkout; an active subscription opens the Stripe
  Billing Portal. Backend errors surface inline next to the button.

  Scenario: Subscribe redirects to Stripe Checkout
    Given a checkout session will be created
    When I click Subscribe on the paywall
    Then the browser is redirected to the Stripe URL

  Scenario: The plan toggle shows each plan's price
    Given a checkout session will be created
    When I open the paywall as the owner
    Then I see the monthly price "$2.99/mo" and the yearly price "$14.99/yr"

  Scenario: Subscribing on the yearly plan sends the yearly plan
    Given a checkout session will be created
    When I pick the yearly plan and click Subscribe
    Then the checkout request used the yearly plan

  Scenario: Subscribe sends the originating page as the cancel path
    Given a checkout session will be created
    When I click Subscribe from the schedule-swap page
    Then the checkout request sent the schedule-swap page as the cancel path

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
