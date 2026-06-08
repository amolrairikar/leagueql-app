Feature: Draft grades (FE-013)
  Each manager's draft is graded for the selected season, with an inline error when
  the draft data fails to load.

  Scenario: Draft grades render when data loads
    Given draft grade data is available
    When I open the draft grades page
    Then I see the manager "Alice"

  Scenario: A pick with no scoring data renders without crashing
    Given draft grade data is available
    When I open the draft grades page
    Then I see the player "Denver Broncos"

  Scenario: A failed load surfaces an inline error
    Given the draft grade data fails to load
    When I open the draft grades page
    Then I see "Failed to load draft data."
