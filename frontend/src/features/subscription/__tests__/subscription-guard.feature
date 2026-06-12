Feature: Subscription access guard (FE-021)
  The guard gates a premium feature's route on the current league's subscription:
  a future end time renders the page, an expired/absent one shows the inline
  paywall. It is a pass-through when billing or the feature's flag is off.

  Scenario: An active subscription renders the gated page
    Given the current league subscription ends in the future
    When I open a gated page behind the subscription guard
    Then I see the gated content "Protected analytics"

  Scenario: An expired subscription shows the inline paywall
    Given the current league subscription has expired
    When I open a gated page behind the subscription guard
    Then I see the paywall heading "Subscription required"

  Scenario: From the paywall a user can return to the dashboard
    Given the current league subscription has expired
    When I open a gated page behind the guard and click back to dashboard
    Then I am routed to the home page

  Scenario: Billing disabled renders the page without a paywall (FE-026)
    Given billing is disabled
    And the current league subscription has expired
    When I open a gated page behind the subscription guard
    Then I see the gated content "Protected analytics"

  Scenario: The feature's paywall flag disabled renders the page without a paywall (FE-026)
    Given the feature paywall flag is disabled
    And the current league subscription has expired
    When I open a gated page behind the subscription guard
    Then I see the gated content "Protected analytics"
