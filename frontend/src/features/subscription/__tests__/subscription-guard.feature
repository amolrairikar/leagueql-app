Feature: Subscription access guard (FE-021)
  The guard gates a premium section on the current league's subscription: a future
  end time renders the gated content, an expired/absent one shows a blurred lock
  overlay in its place (the gated component is never mounted). When the billing
  master flag is off the section is hidden entirely; when only the feature's own
  flag is off the section renders free.

  Scenario: An active subscription renders the gated content
    Given the current league subscription ends in the future
    When I open a gated page behind the subscription guard
    Then I see the gated content "Protected analytics"

  Scenario: An expired subscription shows the locked overlay
    Given the current league subscription has expired
    When I open a gated page behind the subscription guard
    Then I see the paywall heading "Subscription required"

  Scenario: Billing disabled hides the premium section entirely (FE-026)
    Given billing is disabled
    And the current league subscription has expired
    When I open a gated page behind the subscription guard
    Then the gated content "Protected analytics" is not shown

  Scenario: The feature's paywall flag disabled renders the page without a paywall (FE-026)
    Given the feature paywall flag is disabled
    And the current league subscription has expired
    When I open a gated page behind the subscription guard
    Then I see the gated content "Protected analytics"
