Feature: Player records (frontend/player-records)
  All-time player performance records render from the league's box scores, with an
  inline error when the underlying matchup data fails to load.

  Scenario: Player records render when data loads
    Given player box-score data is available
    When I open the player records page
    Then I see the player "Pat Quarterback"

  Scenario: An unplayed 0-0 week's players never surface on a score board
    Given player box-score data includes an unplayed 0-0 week
    When I open the player records page
    Then I do not see the player "Phantom Player"

  Scenario: Postseason performances are excluded by default
    Given player box-score data includes a postseason week
    When I open the player records page
    Then I do not see the player "Playoff Hero"

  Scenario: Toggling to Postseason shows only postseason performances
    Given player box-score data includes a postseason week
    When I open the player records page
    And I switch to postseason records
    Then I see the player "Playoff Hero"
    And I do not see the player "Pat Quarterback"

  Scenario: A failed load surfaces an inline error
    Given the player data fails to load
    When I open the player records page
    Then I see "Failed to load scoring records."
