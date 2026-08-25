Feature: Manager comparison (frontend/manager-comparison)
  Two managers are compared head-to-head; with fewer than two managers the page
  shows a clear zero-state.

  Scenario: A head-to-head comparison renders when data loads
    Given comparison data for two managers is available
    When I open the manager comparison page
    Then I see the manager "Alice"

  Scenario: An unplayed 0-0 week is excluded from records and the game log
    Given comparison data includes an unplayed 0-0 week between the two managers
    When I open the manager comparison page
    Then the record shows "1-0-0" and no phantom tie "1-0-1"
    And the game log has no "0.0" score

  Scenario: Too few managers shows a zero-state
    Given there is no comparison data
    When I open the manager comparison page
    Then I see "Not enough manager data to compare."
