Feature: Transactions nav gating (frontend/transactions, backend/sleeper-transactions, backend/espn-transactions)
  The Transactions nav item is shown for both Sleeper and ESPN leagues, since both
  platforms now produce transaction data.

  Scenario: Sleeper leagues see the Transactions nav item
    Given the current league is on "SLEEPER"
    When I render the sidebar
    Then I see the "Transactions" nav item

  Scenario: ESPN leagues see the Transactions nav item
    Given the current league is on "ESPN"
    When I render the sidebar
    Then I see the "Transactions" nav item
