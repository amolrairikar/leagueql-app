Feature: Playoff-race predictor (frontend/playoff-race-predictor)
  While the latest season's regular season is still in progress there is no
  bracket, so the playoff bracket page shows an interactive predictor: pick the
  remaining regular-season winners and a projected standings table re-sorts live.

  Scenario: The predictor renders for an in-progress season
    Given an in-progress season with unplayed regular-season games
    When I open the playoff bracket page
    Then I see "Playoff Picture"
    And I see the manager "alice"

  Scenario: Picking a winner enables reset
    Given an in-progress season with unplayed regular-season games
    When I open the playoff bracket page
    Then the "Reset picks" control is disabled
    When I pick the winner "alice"
    Then the "Reset picks" control is enabled

  Scenario: The standings table shows a playoff-odds column
    Given an in-progress season with unplayed regular-season games
    When I open the playoff bracket page
    Then I see "Playoff odds"
    And I see "100%"

  Scenario: A finished regular season with no bracket shows the empty state
    Given the latest season's regular season is finished with no bracket
    When I open the playoff bracket page
    Then I see "No playoff bracket for this season yet. It will appear once the playoffs begin."

  Scenario: A played playoff game with no bracket shows the empty state
    Given the latest season has a played playoff game but no bracket
    When I open the playoff bracket page
    Then I see "No playoff bracket for this season yet. It will appear once the playoffs begin."

  Scenario: Clinching scenarios appear when a game is decisive
    Given an in-progress season with unplayed regular-season games
    When I open the playoff bracket page
    Then I see "Clinching scenarios"
    And I see "Win & in"
    And I see "Must win"

  Scenario: Clinching scenarios update when I pick a winner
    Given an in-progress season with unplayed regular-season games
    When I open the playoff bracket page
    Then I see "Win & in"
    When I pick the winner "alice"
    Then I no longer see "Win & in"

  Scenario: No clinching scenarios when nothing is decided
    Given an early season with nothing decided
    When I open the playoff bracket page
    Then I see "Playoff Picture"
    And I do not see "Clinching scenarios"
