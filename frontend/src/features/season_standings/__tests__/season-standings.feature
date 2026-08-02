Feature: Season standings (FE-005)
  The standings page shows the selected season's standings (including a
  strength-of-schedule column derived from the season's matchups) and surfaces
  an inline error if the data fails to load.

  Scenario: Standings render when data loads
    Given season standings data is available
    When I open the standings page
    Then I see the manager "Alice"

  Scenario: Expected wins average the schedule-swap simulation
    Given season standings data is available
    When I open the standings page
    Then the expected wins for "Alice" is "1.0"
    And the expected wins for "Bob" is "0.0"

  Scenario: Strength of schedule reflects opponents faced
    Given season standings data is available
    When I open the standings page
    Then the schedule strength for "Alice" is "0.000"
    And the schedule strength for "Bob" is "1.000"

  Scenario: Derived columns show a dash when matchups are missing
    Given season standings data is available but matchups are missing
    When I open the standings page
    Then the schedule strength for "Alice" is "—"
    And the expected wins for "Alice" is "—"

  Scenario: The current season with no champion shows an in-progress state
    Given champion-less standings for the latest season
    When I open the standings page
    Then I see the season champion "Season in progress"

  Scenario: A failed load surfaces an inline error
    Given the standings data fails to load
    When I open the standings page
    Then I see "Failed to load standings."
