Feature: Owner-gated sidebar actions (backend/league-authorization / frontend/ownership-transfer)
  The sidebar shows owner-only actions only to the league owner; non-owners see
  the dashboard and a way to claim ownership. Refresh League is additionally
  ESPN-only, since Sleeper leagues refresh automatically.

  Scenario: The ESPN owner sees the owner-only actions
    Given I am the owner of the current ESPN league
    When I render the sidebar
    Then I see the "Refresh League" action
    And I see the "Delete League" action
    And I see the "Transfer Ownership" action
    And I do not see the "Claim Ownership" action

  Scenario: A non-owner sees no owner actions
    Given I am not the owner of the current ESPN league
    When I render the sidebar
    Then I see the "Claim Ownership" action
    And I do not see the "Refresh League" action
    And I do not see the "Delete League" action
    And I do not see the "Transfer Ownership" action

  Scenario: A Sleeper owner does not see Refresh League
    Given I am the owner of the current Sleeper league
    When I render the sidebar
    Then I see the "Delete League" action
    And I see the "Transfer Ownership" action
    And I do not see the "Refresh League" action
