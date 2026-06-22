Feature: Matchups and box scores (FE-006)
  The matchups page lists a season/week's matchups and surfaces an inline error
  when the data fails to load.

  Scenario: Matchups render when data loads
    Given matchup data is available
    When I open the matchups page
    Then I see the manager "Alice"

  Scenario: A failed load surfaces an inline error
    Given the matchup data fails to load
    When I open the matchups page
    Then I see "Failed to load matchups."

  Scenario: The weekly recap loads for the latest week on first render
    Given matchup and recap data are available
    When I open the matchups page
    Then I see the recap headline "Week 1 Recap: Alice Cruises"
