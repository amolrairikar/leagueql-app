Feature: Draft recap (FE-012)
  The draft board renders the selected season's picks and surfaces an inline error
  when the draft data fails to load.

  Scenario: The draft board renders when data loads
    Given draft data is available
    When I open the draft recap page
    Then I see the player "Pat Quarterback"

  Scenario: A failed load surfaces an inline error
    Given the draft data fails to load
    When I open the draft recap page
    Then I see "Failed to load draft data."
