Feature: Manager history (frontend/manager-history)
  The manager history page shows each manager's per-season records and rivalries,
  with an inline error when the data fails to load.

  Scenario: Manager history renders when data loads
    Given manager history data is available
    When I open the manager history page
    Then I see the manager "Alice"

  Scenario: A failed load surfaces an inline error
    Given the manager history data fails to load
    When I open the manager history page
    Then I see "Failed to load manager data."
