Feature: Manager comparison (frontend/manager-comparison)
  Two managers are compared head-to-head; with fewer than two managers the page
  shows a clear zero-state.

  Scenario: A head-to-head comparison renders when data loads
    Given comparison data for two managers is available
    When I open the manager comparison page
    Then I see the manager "Alice"

  Scenario: Too few managers shows a zero-state
    Given there is no comparison data
    When I open the manager comparison page
    Then I see "Not enough manager data to compare."
