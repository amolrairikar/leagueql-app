Feature: Draft recap (FE-012)
  The draft board renders the selected season's picks and surfaces an inline error
  when the draft data fails to load.

  Scenario: The draft board renders when data loads
    Given draft data is available
    When I open the draft recap page
    Then I see the player "Pat Quarterback"

  Scenario: A pick with no scoring data renders without crashing
    Given draft data is available
    When I open the draft recap page
    Then I see the player "Denver Broncos"

  Scenario: A pick traded to another manager renders in its slot with a traded badge
    Given draft data with a traded pick is available
    When I open the draft recap page
    Then I see the player "Traded Pick"
    And the pick is badged as traded to "Alice"

  Scenario: A failed load surfaces an inline error
    Given the draft data fails to load
    When I open the draft recap page
    Then I see "Failed to load draft data."
