Feature: Season standings (FE-005)
  The standings page shows the selected season's standings and surfaces an inline
  error if the data fails to load.

  Scenario: Standings render when data loads
    Given season standings data is available
    When I open the standings page
    Then I see the manager "Alice"

  Scenario: A failed load surfaces an inline error
    Given the standings data fails to load
    When I open the standings page
    Then I see "Failed to load standings."
