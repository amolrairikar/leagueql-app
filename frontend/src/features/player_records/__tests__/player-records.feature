Feature: Player records (frontend/player-records)
  All-time player performance records render from the league's box scores, with an
  inline error when the underlying matchup data fails to load.

  Scenario: Player records render when data loads
    Given player box-score data is available
    When I open the player records page
    Then I see the player "Pat Quarterback"

  Scenario: A failed load surfaces an inline error
    Given the player data fails to load
    When I open the player records page
    Then I see "Failed to load scoring records."
