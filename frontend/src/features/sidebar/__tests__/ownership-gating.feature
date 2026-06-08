Feature: Owner-gated sidebar actions (LQL-01 / FE-025)
  The sidebar shows owner-only actions only to the league owner; non-owners see
  the dashboard and a way to claim ownership.

  Scenario: The owner sees the owner-only actions
    Given I am the owner of the current league
    When I render the sidebar
    Then I see the "Refresh League" action
    And I see the "Delete League" action
    And I see the "Transfer Ownership" action
    And I do not see the "Claim Ownership" action

  Scenario: A non-owner sees no owner actions
    Given I am not the owner of the current league
    When I render the sidebar
    Then I see the "Claim Ownership" action
    And I do not see the "Refresh League" action
    And I do not see the "Delete League" action
    And I do not see the "Transfer Ownership" action

  Scenario: Billing disabled hides Manage Subscription for the owner (FE-026)
    Given billing is disabled
    And I am the owner of the current league
    When I render the sidebar
    Then I see the "Refresh League" action
    And I do not see the "Manage Subscription" action
