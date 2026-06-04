Feature: Subscription access guard (FE-021)
  The guard gates analytics pages on the current league's subscription: a future
  end time renders the page, an expired/absent one shows the inline paywall.

  Scenario: An active subscription renders the gated page
    Given the current league subscription ends in the future
    When I open a gated page behind the subscription guard
    Then I see the gated content "Protected analytics"

  Scenario: An expired subscription shows the inline paywall
    Given the current league subscription has expired
    When I open a gated page behind the subscription guard
    Then I see the paywall heading "Subscription required"
