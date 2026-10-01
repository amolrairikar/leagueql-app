Feature: Lineup backfill notification bell (frontend/lineup-data-status)
  A Yahoo league whose weekly player scores are still being backfilled (or couldn't
  be loaded yet) shows a header bell explaining which seasons are affected.

  Scenario: Seasons still loading
    Given a Yahoo league with pending lineup seasons "2019,2020,2021,2024"
    When I render the lineup bell
    Then I see the bell indicator
    When I open the bell
    Then I see "Player box scores for 2019–2021, 2024 are still loading"

  Scenario: A season that couldn't be loaded yet
    Given a Yahoo league with failed lineup season "2019"
    When I render the lineup bell
    And I open the bell
    Then I see "Couldn't load player scores for 2019 yet"

  Scenario: Nothing pending hides the bell
    Given a Yahoo league with no pending lineup seasons
    When I render the lineup bell
    Then I do not see the bell

  Scenario: A failed metadata request hides the bell
    Given the league metadata request fails
    When I render the lineup bell
    Then I do not see the bell

  Scenario: Non-Yahoo leagues never show the bell
    Given a Sleeper league
    When I render the lineup bell for a Sleeper league
    Then I do not see the bell
