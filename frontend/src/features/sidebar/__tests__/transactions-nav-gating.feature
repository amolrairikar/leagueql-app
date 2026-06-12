Feature: Transactions nav gating (FE-027 / BE-019)
  The Transactions nav item is shown only for Sleeper leagues, since ESPN
  leagues have no transaction data.

  Scenario: Sleeper leagues see the Transactions nav item
    Given the current league is on "SLEEPER"
    When I render the sidebar
    Then I see the "Transactions" nav item

  Scenario: ESPN leagues do not see the Transactions nav item
    Given the current league is on "ESPN"
    When I render the sidebar
    Then I do not see the "Transactions" nav item
