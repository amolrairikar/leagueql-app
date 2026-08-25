Feature: Matchup records (frontend/matchup-records)
  All-time team/matchup superlatives render from the league's matchups, with an
  inline error when the data fails to load.

  Scenario: Matchup records render when data loads
    Given matchup records data is available
    When I open the matchup records page
    Then I see the manager "Alice"

  Scenario: Both teams in one matchup rank in the Lowest Team Score card
    Given matchup records data is available
    When I open the matchup records page
    Then the "Lowest Team Score" card lists both "Alice" and "Bob"

  Scenario: An unplayed 0-0 matchup never surfaces on a record board
    Given matchup records data includes an unplayed 0-0 week
    When I open the matchup records page
    Then the "Lowest Team Score" card does not list "Cara"

  Scenario: A failed load surfaces an inline error
    Given the matchup records data fails to load
    When I open the matchup records page
    Then I see "Failed to load matchup records."
