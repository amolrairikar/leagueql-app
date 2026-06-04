Feature: Matchup records (FE-011)
  All-time team/matchup superlatives render from the league's matchups, with an
  inline error when the data fails to load.

  Scenario: Matchup records render when data loads
    Given matchup records data is available
    When I open the matchup records page
    Then I see the manager "Alice"

  Scenario: A failed load surfaces an inline error
    Given the matchup records data fails to load
    When I open the matchup records page
    Then I see "Failed to load matchup records."
