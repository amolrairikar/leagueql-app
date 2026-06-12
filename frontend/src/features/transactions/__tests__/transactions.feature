Feature: Transactions (FE-027)
  The transactions page lists a season's completed Sleeper transactions and
  surfaces an empty state or an inline error depending on the API response.

  Scenario: Transactions render when data loads
    Given transactions data is available
    When I open the transactions page
    Then I see "Pat Quarterback"
    And I see "Trade"

  Scenario: A season with no transactions shows an empty state
    Given the league has no transactions
    When I open the transactions page
    Then I see "No transactions for this season."

  Scenario: A failed load surfaces an inline error
    Given the transactions data fails to load
    When I open the transactions page
    Then I see "Failed to load transactions."
