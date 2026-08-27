Feature: Playoff bracket (frontend/playoff-bracket)
  The winners'-bracket tree renders for the selected season, with an inline error
  when the bracket data fails to load.

  Scenario: The bracket renders when data loads
    Given playoff bracket data is available
    When I open the playoff bracket page
    Then I see the manager "Alice"

  Scenario: A failed load surfaces an inline error
    Given the playoff bracket data fails to load
    When I open the playoff bracket page
    Then I see "Failed to load playoff bracket data."

  Scenario: An in-progress latest season shows the predictor instead of the empty state
    Given the latest season is in progress with games still to play
    When I open the playoff bracket page
    Then I see "Playoff Picture"

  Scenario: A season with no bracket shows an empty state
    Given the selected season has no playoff bracket
    When I open the playoff bracket page
    Then I see "No playoff bracket for this season yet. It will appear once the playoffs begin."

  Scenario: A bracket with byes renders the wildcard round matchups
    Given a six-team bracket with byes is available
    When I open the playoff bracket page
    Then I see the manager "Gil"
    And I see the manager "Alice"
