Feature: Landing page connect routing (FE-001 / FE-002 / FE-025)
  Connecting from the landing page routes ESPN leagues that need onboarding to the
  connect form, and opens the Join League dialog for leagues the caller isn't a
  member of yet.

  Scenario: Connecting an ESPN league I am not a member of opens the Join dialog
    Given the ESPN league read is member-gated for me
    When I submit an ESPN league ID from the landing page
    Then I see the "Join league" dialog
    When I verify my ESPN membership in the dialog
    Then I am routed to the home page

  Scenario: The pricing table shows the plans and premium features
    Given billing is enabled
    When I open the landing page
    Then I see the "Monthly" plan priced "$1.99"
    And I see the "Yearly" plan priced "$8.99"
    And I see "Schedule-swap simulator" listed as a premium feature
    And I see "Weekly awards" listed as a premium feature
    And I see "Weekly recap" listed as a premium feature

  Scenario: With billing disabled the pricing table is hidden
    Given billing is disabled
    When I open the landing page
    Then the pricing table is not shown
